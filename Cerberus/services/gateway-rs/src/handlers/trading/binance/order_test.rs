mod upstream;
mod validation;

use axum::{
    extract::{Extension, State},
    http::StatusCode,
    Json,
};

use crate::event_bus::publish_order_event;
use crate::gateway_types::{AppState, BinanceTestOrderRequest, RequestContext};
use crate::handlers::common::{error_body, with_request_id};

use upstream::submit_order_test_upstream;
use validation::validate_order_test_input;

pub(crate) async fn binance_order_test(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
    Json(req): Json<BinanceTestOrderRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let request_id = ctx.request_id.as_str();
    let api_key = state.exchange.binance_api_key.as_deref().ok_or((
        StatusCode::SERVICE_UNAVAILABLE,
        error_body("config_error", "BINANCE_API_KEY not configured", request_id),
    ))?;
    let api_secret = state.exchange.binance_api_secret.as_deref().ok_or((
        StatusCode::SERVICE_UNAVAILABLE,
        error_body(
            "config_error",
            "BINANCE_API_SECRET not configured",
            request_id,
        ),
    ))?;

    let prepared = validate_order_test_input(&state, &req, request_id)?;
    let payload = submit_order_test_upstream(&state, &prepared, api_key, api_secret, request_id).await?;

    publish_order_event(
        &state,
        "trade.executions.binance-test".to_string(),
        serde_json::json!({
            "event": "binance.order_test.submitted",
            "provider": "binance",
            "account_id": "binance-test",
            "symbol": prepared.symbol,
            "status": "submitted",
            "request_id": request_id,
            "response": payload.clone()
        }),
    )
    .await;

    Ok(Json(with_request_id(payload, request_id)))
}
