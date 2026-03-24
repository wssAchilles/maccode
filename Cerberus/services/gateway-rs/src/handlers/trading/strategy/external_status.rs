use std::time::Duration;

use axum::{
    extract::{Extension, State},
    Json,
};

use crate::gateway_types::{AppState, RequestContext, REQUEST_ID_HEADER};

pub(crate) async fn get_external_status(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
) -> impl axum::response::IntoResponse {
    let strategy_status = if let Some(base) = state.strategy_base_url.as_ref() {
        let health_url = format!("{base}/health");
        match state
            .http_client
            .get(health_url.clone())
            .header(REQUEST_ID_HEADER, ctx.request_id.as_str())
            .timeout(Duration::from_millis(1500))
            .send()
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
                    "reachable": status.is_success(),
                    "status_code": status.as_u16(),
                    "health": body
                })
            }
            Err(err) => serde_json::json!({
                "configured": true,
                "base_url": base,
                "health_url": health_url,
                "reachable": false,
                "error": err.to_string()
            }),
        }
    } else {
        serde_json::json!({
            "configured": false,
            "reachable": false
        })
    };

    Json(serde_json::json!({
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
        "request_id": ctx.request_id
    }))
}
