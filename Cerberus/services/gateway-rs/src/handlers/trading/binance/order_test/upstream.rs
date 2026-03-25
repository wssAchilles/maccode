use axum::{http::StatusCode, Json};

use crate::gateway_types::AppState;
use crate::gateway_utils::{normalize_http_path, sign_binance_query, to_axum_status};
use crate::handlers::common::{error_body, internal_err_json};

use super::validation::PreparedBinanceOrderTest;

pub(super) async fn submit_order_test_upstream(
    state: &AppState,
    prepared: &PreparedBinanceOrderTest,
    api_key: &str,
    api_secret: &str,
    request_id: &str,
) -> Result<serde_json::Value, (StatusCode, Json<serde_json::Value>)> {
    let query = serde_urlencoded::to_string(&prepared.params)
        .map_err(|err| internal_err_json(request_id, "serialization_error", err))?;
    let signature = sign_binance_query(api_secret, &query).map_err(|(status, message)| {
        (status, error_body("signature_error", message, request_id))
    })?;
    let body = format!("{query}&signature={signature}");
    let path = normalize_http_path(&state.exchange.binance_order_test_path);
    let url = format!(
        "{}{}",
        state.exchange.binance_api_base.trim_end_matches('/'),
        path
    );

    let resp = state
        .http_client
        .post(url)
        .header("X-MBX-APIKEY", api_key)
        .header("Content-Type", "application/x-www-form-urlencoded")
        .body(body)
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
        serde_json::json!({ "ok": true })
    } else {
        serde_json::from_str::<serde_json::Value>(&text)
            .unwrap_or_else(|_| serde_json::json!({ "raw": text }))
    };

    Ok(payload)
}
