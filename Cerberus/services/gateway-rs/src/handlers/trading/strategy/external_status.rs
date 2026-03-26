use axum::{
    extract::{Extension, State},
    Json,
};

use crate::gateway_types::{AppState, RequestContext, REQUEST_ID_HEADER};
use crate::handlers::common::with_request_context;
use crate::handlers::trading::strategy::upstream::send_strategy_request;

pub(crate) async fn get_external_status(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
) -> impl axum::response::IntoResponse {
    let strategy_status = if let Some(base) = state.strategy_base_url.as_ref() {
        let health_url = format!("{base}/health");
        let request = state
            .http_client
            .get(health_url.clone())
            .header(REQUEST_ID_HEADER, ctx.request_id.as_str());
        match send_strategy_request(&state, request, state.strategy_upstream.health_timeout_ms)
            .await
        {
            Ok(resp) => {
                let status = resp.status();
                let body = resp
                    .json::<serde_json::Value>()
                    .await
                    .unwrap_or_else(|_| serde_json::json!({}));
                serde_json::json!({
                    "configured": true,
                    "base_url": base,
                    "health_url": health_url,
                    "auth_enabled": state.strategy_internal_auth.enabled,
                    "reachable": status.is_success(),
                    "status_code": status.as_u16(),
                    "health": body
                })
            }
            Err(err) => {
                let error_text = err.client_message();
                let retry_after_ms = err.retry_after_ms();
                serde_json::json!({
                    "configured": true,
                    "base_url": base,
                    "health_url": health_url,
                    "auth_enabled": state.strategy_internal_auth.enabled,
                    "reachable": false,
                    "retry_after_ms": retry_after_ms,
                    "error": error_text
                })
            }
        }
    } else {
        serde_json::json!({
            "configured": false,
            "reachable": false
        })
    };

    Json(with_request_context(
        serde_json::json!({
            "binance": {
                "api_base": state.exchange.binance_api_base,
                "order_test_path": state.exchange.binance_order_test_path,
                "has_key": state.exchange.binance_api_key.is_some(),
                "has_secret": state.exchange.binance_api_secret.is_some()
            },
            "alpaca": {
                "trading_base": state.exchange.alpaca_trading_base,
                "has_key": state.exchange.alpaca_api_key.is_some(),
                "has_secret": state.exchange.alpaca_api_secret.is_some()
            },
            "strategy": strategy_status,
        }),
        ctx.request_id.as_str(),
        ctx.idempotency_key.as_deref(),
    ))
}
