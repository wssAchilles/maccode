use crate::gateway_types::{AppState, REQUEST_ID_HEADER};
use crate::handlers::trading::strategy::summary::model::{
    AggregateSummaryComponent, AggregateSummaryPayload, StrategySummaryPayload,
    SummaryComponentEnvelope,
};
use crate::handlers::trading::strategy::summary::params::SummaryRequest;
use crate::handlers::trading::strategy::upstream::send_strategy_request;
use tracing::warn;

pub(super) async fn fetch_strategy_summary_aggregate(
    state: &AppState,
    strategy_base: &str,
    request_id: &str,
    idempotency_key: Option<&str>,
    request: &SummaryRequest,
) -> Option<StrategySummaryPayload> {
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

    let payload = match response.json::<AggregateSummaryPayload>().await {
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

    if !payload.has_required_components() {
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
    aggregate: &AggregateSummaryPayload,
    request: &SummaryRequest,
) -> StrategySummaryPayload {
    StrategySummaryPayload {
        strategy_base_url: strategy_base.to_string(),
        symbol: aggregate
            .symbol
            .as_deref()
            .filter(|value| !value.is_empty())
            .unwrap_or(request.symbol.as_str())
            .to_string(),
        source: aggregate
            .source
            .as_deref()
            .filter(|value| !value.is_empty())
            .unwrap_or(request.source.as_str())
            .to_string(),
        recent_limit: aggregate
            .recent_limit
            .unwrap_or(request.recent_limit as u64),
        orderbook_depth: aggregate
            .orderbook_depth
            .unwrap_or(request.orderbook_depth as u64),
        aggregation_mode: "strategy_aggregate",
        signal: from_aggregate_component(&aggregate.signal),
        recent_signals: from_aggregate_component(&aggregate.recent_signals),
        persistence: from_aggregate_component(&aggregate.persistence),
        matching_orderbook: from_aggregate_component(&aggregate.matching_orderbook),
    }
}

fn from_aggregate_component(component: &AggregateSummaryComponent) -> SummaryComponentEnvelope {
    SummaryComponentEnvelope {
        ok: component.ok,
        status_code: component.status_code,
        url: None,
        payload: component.payload.clone(),
        error: component.error.clone(),
        retry_after_ms: component.retry_after_ms,
    }
}
