use axum::{
    extract::{Extension, Path, State},
    http::StatusCode,
    Json,
};

use crate::event_bus::publish_order_event;
use crate::gateway_types::{AppState, RequestContext};
use crate::gateway_utils::to_axum_status;
use crate::handlers::common::{error_body, internal_err_json, with_request_id};

pub(crate) async fn cancel_alpaca_order(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
    Path(order_id): Path<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let request_id = ctx.request_id.as_str();
    if order_id.trim().is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            error_body("validation_error", "order_id is required", request_id),
        ));
    }

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

    let url = format!(
        "{}/orders/{}",
        state.exchange.alpaca_trading_base.trim_end_matches('/'),
        order_id
    );
    let resp = state
        .http_client
        .delete(url)
        .header("APCA-API-KEY-ID", api_key)
        .header("APCA-API-SECRET-KEY", api_secret)
        .send()
        .await
        .map_err(|err| internal_err_json(request_id, "upstream_request_failed", err))?;

    let status = resp.status();
    let text = resp
        .text()
        .await
        .map_err(|err| internal_err_json(request_id, "upstream_decode_failed", err))?;
    if !status.is_success() {
        return Err((
            to_axum_status(status),
            error_body("upstream_error", text, request_id),
        ));
    }
    let payload = if text.trim().is_empty() {
        serde_json::json!({
            "ok": true,
            "canceled": true,
            "order_id": order_id.clone()
        })
    } else {
        serde_json::from_str::<serde_json::Value>(&text)
            .unwrap_or_else(|_| serde_json::json!({ "raw": text }))
    };

    publish_order_event(
        &state,
        "trade.executions.alpaca-paper".to_string(),
        serde_json::json!({
            "event": "alpaca.order.canceled",
            "provider": "alpaca",
            "account_id": "alpaca-paper",
            "order_id": order_id,
            "status": "canceled",
            "request_id": request_id,
            "response": payload.clone()
        }),
    )
    .await;

    Ok(Json(with_request_id(payload, request_id)))
}
