use crate::gateway_types::{AppState, REQUEST_ID_HEADER};
use crate::handlers::trading::strategy::summary::downstream_errors::{
    normalize_downstream_error, render_upstream_send_error, structured_error,
};
use crate::handlers::trading::strategy::summary::model::{
    StrategySummaryPayload, SummaryComponentEnvelope,
};
use crate::handlers::trading::strategy::summary::params::SummaryRequest;
use crate::handlers::trading::strategy::upstream::send_strategy_request;

pub(super) async fn fetch_strategy_summary_fanout(
    state: &AppState,
    strategy_base: &str,
    request_id: &str,
    idempotency_key: Option<&str>,
    request: &SummaryRequest,
) -> StrategySummaryPayload {
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

    StrategySummaryPayload {
        strategy_base_url: strategy_base.to_string(),
        symbol: request.symbol.clone(),
        source: request.source.clone(),
        recent_limit: request.recent_limit as u64,
        orderbook_depth: request.orderbook_depth as u64,
        aggregation_mode: "gateway_fanout",
        signal,
        recent_signals: recent,
        persistence,
        matching_orderbook: orderbook,
    }
}

async fn fetch_strategy_json(
    state: &AppState,
    strategy_base: &str,
    path_and_query: &str,
    request_id: &str,
    idempotency_key: Option<&str>,
) -> SummaryComponentEnvelope {
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
                        SummaryComponentEnvelope {
                            ok: true,
                            status_code: status.as_u16(),
                            url: Some(url),
                            payload: Some(payload),
                            error: None,
                            retry_after_ms: None,
                        }
                    } else {
                        let error = normalize_downstream_error(&payload, status, request_id);
                        SummaryComponentEnvelope {
                            ok: false,
                            status_code: status.as_u16(),
                            url: Some(url),
                            payload: Some(payload),
                            error: Some(error),
                            retry_after_ms: None,
                        }
                    }
                }
                Err(err) => SummaryComponentEnvelope {
                    ok: false,
                    status_code: status.as_u16(),
                    url: Some(url),
                    payload: None,
                    error: Some(structured_error(
                        "upstream_decode_failed",
                        format!("decode failed: {err}"),
                        request_id,
                    )),
                    retry_after_ms: None,
                },
            }
        }
        Err(err) => render_upstream_send_error(err, url.as_str(), request_id),
    }
}
