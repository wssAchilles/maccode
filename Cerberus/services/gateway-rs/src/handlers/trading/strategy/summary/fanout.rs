use crate::gateway_types::{AppState, REQUEST_ID_HEADER};
use crate::handlers::trading::strategy::summary::downstream_errors::{
    normalize_downstream_error, render_upstream_send_error, structured_error,
};
use crate::handlers::trading::strategy::summary::params::SummaryRequest;
use crate::handlers::trading::strategy::upstream::send_strategy_request;

pub(super) async fn fetch_strategy_summary_fanout(
    state: &AppState,
    strategy_base: &str,
    request_id: &str,
    idempotency_key: Option<&str>,
    request: &SummaryRequest,
) -> serde_json::Value {
    let signal_path = "/api/v1/signal".to_string();
    let recent_path = format!(
        "/api/v1/signals/recent?limit={}&source={}",
        request.recent_limit, request.source
    );
    let persistence_path = "/api/v1/status/persistence".to_string();
    let orderbook_path = format!(
        "/api/v1/matching/orderbook?symbol={}&depth={}",
        request.symbol, request.orderbook_depth
    );

    let (signal, recent, persistence, orderbook) = tokio::join!(
        fetch_strategy_json(
            state,
            strategy_base,
            &signal_path,
            request_id,
            idempotency_key,
        ),
        fetch_strategy_json(
            state,
            strategy_base,
            &recent_path,
            request_id,
            idempotency_key,
        ),
        fetch_strategy_json(
            state,
            strategy_base,
            &persistence_path,
            request_id,
            idempotency_key,
        ),
        fetch_strategy_json(
            state,
            strategy_base,
            &orderbook_path,
            request_id,
            idempotency_key,
        ),
    );

    serde_json::json!({
        "strategy_base_url": strategy_base,
        "symbol": request.symbol,
        "source": request.source,
        "recent_limit": request.recent_limit,
        "orderbook_depth": request.orderbook_depth,
        "aggregation_mode": "gateway_fanout",
        "signal": signal,
        "recent_signals": recent,
        "persistence": persistence,
        "matching_orderbook": orderbook,
    })
}

async fn fetch_strategy_json(
    state: &AppState,
    strategy_base: &str,
    path_and_query: &str,
    request_id: &str,
    idempotency_key: Option<&str>,
) -> serde_json::Value {
    let url = format!("{}{}", strategy_base.trim_end_matches('/'), path_and_query);
    let mut req = state
        .http_client
        .get(url.clone())
        .header(REQUEST_ID_HEADER, request_id);
    if let Some(key) = idempotency_key {
        req = req.header("idempotency-key", key);
    }

    match send_strategy_request(state, req, state.strategy_upstream.timeout_ms).await {
        Ok(resp) => {
            let status = resp.status();
            match resp.json::<serde_json::Value>().await {
                Ok(payload) => {
                    if status.is_success() {
                        serde_json::json!({
                            "ok": true,
                            "status_code": status.as_u16(),
                            "url": url,
                            "payload": payload
                        })
                    } else {
                        let error = normalize_downstream_error(&payload, status, request_id);
                        serde_json::json!({
                            "ok": false,
                            "status_code": status.as_u16(),
                            "url": url,
                            "payload": payload,
                            "error": error
                        })
                    }
                }
                Err(err) => serde_json::json!({
                    "ok": false,
                    "status_code": status.as_u16(),
                    "url": url,
                    "error": structured_error(
                        "upstream_decode_failed",
                        format!("decode failed: {err}"),
                        request_id
                    )
                }),
            }
        }
        Err(err) => render_upstream_send_error(err, url.as_str(), request_id),
    }
}
