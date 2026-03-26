use crate::gateway_types::{AppState, REQUEST_ID_HEADER};
use crate::handlers::trading::strategy::summary::params::SummaryRequest;
use crate::handlers::trading::strategy::upstream::send_strategy_request;
use tracing::warn;

pub(super) async fn fetch_strategy_summary_aggregate(
    state: &AppState,
    strategy_base: &str,
    request_id: &str,
    idempotency_key: Option<&str>,
    request: &SummaryRequest,
) -> Option<serde_json::Value> {
    let aggregate_path = format!(
        "/api/v1/summary?symbol={}&recent_limit={}&source={}&orderbook_depth={}",
        request.symbol, request.recent_limit, request.source, request.orderbook_depth
    );
    let aggregate_url = format!("{}{}", strategy_base.trim_end_matches('/'), aggregate_path);
    let mut upstream_request = state
        .http_client
        .get(aggregate_url.as_str())
        .header(REQUEST_ID_HEADER, request_id);
    if let Some(key) = idempotency_key {
        upstream_request = upstream_request.header("idempotency-key", key);
    }

    let response =
        match send_strategy_request(state, upstream_request, state.strategy_upstream.timeout_ms)
            .await
        {
            Ok(response) => response,
            Err(err) => {
                warn!(
                    request_id,
                    url = %aggregate_url,
                    reason = %err.telemetry_reason(),
                    "strategy aggregate summary request failed; fallback to gateway fan-out"
                );
                return None;
            }
        };

    if !response.status().is_success() {
        warn!(
            request_id,
            url = %aggregate_url,
            status_code = response.status().as_u16(),
            "strategy aggregate summary returned non-success; fallback to gateway fan-out"
        );
        return None;
    }

    let payload = match response.json::<serde_json::Value>().await {
        Ok(payload) => payload,
        Err(err) => {
            warn!(
                request_id,
                url = %aggregate_url,
                reason = %err,
                "strategy aggregate summary decode failed; fallback to gateway fan-out"
            );
            return None;
        }
    };

    if !validate_strategy_aggregate_payload(&payload) {
        warn!(
            request_id,
            url = %aggregate_url,
            "strategy aggregate summary shape mismatch; fallback to gateway fan-out"
        );
        return None;
    }

    Some(build_summary_payload_from_aggregate(
        strategy_base,
        &payload,
        request,
    ))
}

fn build_summary_payload_from_aggregate(
    strategy_base: &str,
    aggregate: &serde_json::Value,
    request: &SummaryRequest,
) -> serde_json::Value {
    serde_json::json!({
        "strategy_base_url": strategy_base,
        "symbol": aggregate
            .get("symbol")
            .and_then(|value| value.as_str())
            .filter(|value| !value.is_empty())
            .unwrap_or(request.symbol.as_str()),
        "source": aggregate
            .get("source")
            .and_then(|value| value.as_str())
            .filter(|value| !value.is_empty())
            .unwrap_or(request.source.as_str()),
        "recent_limit": aggregate
            .get("recent_limit")
            .and_then(|value| value.as_u64())
            .unwrap_or(request.recent_limit as u64),
        "orderbook_depth": aggregate
            .get("orderbook_depth")
            .and_then(|value| value.as_u64())
            .unwrap_or(request.orderbook_depth as u64),
        "aggregation_mode": "strategy_aggregate",
        "signal": aggregate.get("signal").cloned().unwrap_or(serde_json::Value::Null),
        "recent_signals": aggregate
            .get("recent_signals")
            .cloned()
            .unwrap_or(serde_json::Value::Null),
        "persistence": aggregate
            .get("persistence")
            .cloned()
            .unwrap_or(serde_json::Value::Null),
        "matching_orderbook": aggregate
            .get("matching_orderbook")
            .cloned()
            .unwrap_or(serde_json::Value::Null),
    })
}

fn validate_strategy_aggregate_payload(payload: &serde_json::Value) -> bool {
    has_summary_component(payload, "signal")
        && has_summary_component(payload, "recent_signals")
        && has_summary_component(payload, "persistence")
        && has_summary_component(payload, "matching_orderbook")
}

fn has_summary_component(payload: &serde_json::Value, field: &str) -> bool {
    let Some(component) = payload.get(field).and_then(serde_json::Value::as_object) else {
        return false;
    };

    component.contains_key("ok")
        && component.contains_key("status_code")
        && (component.contains_key("payload") || component.contains_key("error"))
}
