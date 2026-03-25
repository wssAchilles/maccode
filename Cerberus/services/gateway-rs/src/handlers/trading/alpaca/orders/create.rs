mod upstream;
mod validation;

use axum::{
    extract::{Extension, State},
    http::StatusCode,
    Json,
};

use crate::event_bus::publish_order_event;
use crate::gateway_types::{AlpacaOrderRequest, AppState, RequestContext};
use crate::handlers::common::{error_body, with_request_id};

use upstream::submit_alpaca_upstream;
use validation::validate_alpaca_create;

pub(crate) async fn create_alpaca_order(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
    Json(req): Json<AlpacaOrderRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let request_id = ctx.request_id.as_str();
    let api_key = state.exchange.alpaca_api_key.as_deref().ok_or((
        StatusCode::SERVICE_UNAVAILABLE,
        error_body("config_error", "ALPACA_API_KEY not configured", request_id),
    ))?;
    let api_secret = state.exchange.alpaca_api_secret.as_deref().ok_or((
        StatusCode::SERVICE_UNAVAILABLE,
        error_body(
            "config_error",
            "ALPACA_API_SECRET not configured",
            request_id,
        ),
    ))?;

    let prepared = validate_alpaca_create(&state, &req, request_id)?;
    let payload =
        submit_alpaca_upstream(&state, &prepared.payload, api_key, api_secret, request_id).await?;

    let order_id = payload
        .get("id")
        .and_then(|value| value.as_str())
        .unwrap_or_default()
        .to_string();
    let status_name = payload
        .get("status")
        .and_then(|value| value.as_str())
        .unwrap_or("submitted")
        .to_string();

    publish_order_event(
        &state,
        "trade.executions.alpaca-paper".to_string(),
        serde_json::json!({
            "event": "alpaca.order.submitted",
            "provider": "alpaca",
            "account_id": "alpaca-paper",
            "order_id": order_id,
            "symbol": prepared.symbol,
            "status": status_name,
            "request_id": request_id,
            "response": payload.clone()
        }),
    )
    .await;

    Ok(Json(with_request_id(payload, request_id)))
}
