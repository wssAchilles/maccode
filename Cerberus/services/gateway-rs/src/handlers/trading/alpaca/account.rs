use axum::{
    extract::{Extension, State},
    http::StatusCode,
    Json,
};

use crate::gateway_types::{AppState, RequestContext};
use crate::gateway_utils::to_axum_status;
use crate::handlers::common::{error_body, internal_err_json};

pub(crate) async fn get_alpaca_account(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
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

    let url = format!(
        "{}/account",
        state.exchange.alpaca_trading_base.trim_end_matches('/')
    );
    let resp = state
        .http_client
        .get(url)
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
    let payload = serde_json::from_str::<serde_json::Value>(&text)
        .unwrap_or_else(|_| serde_json::json!({ "raw": text }));
    Ok(Json(payload))
}
