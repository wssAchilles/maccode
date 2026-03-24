use axum::{http::StatusCode, Json};

use crate::gateway_types::AppState;
use crate::gateway_utils::to_axum_status;
use crate::handlers::common::{error_body, internal_err_json};

pub(super) async fn submit_alpaca_upstream(
    state: &AppState,
    payload: &serde_json::Value,
    api_key: &str,
    api_secret: &str,
    request_id: &str,
) -> Result<serde_json::Value, (StatusCode, Json<serde_json::Value>)> {
    let url = format!(
        "{}/orders",
        state.exchange.alpaca_trading_base.trim_end_matches('/')
    );
    let resp = state
        .http_client
        .post(url)
        .header("APCA-API-KEY-ID", api_key)
        .header("APCA-API-SECRET-KEY", api_secret)
        .json(payload)
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

    Ok(serde_json::from_str::<serde_json::Value>(&text)
        .unwrap_or_else(|_| serde_json::json!({ "raw": text })))
}
