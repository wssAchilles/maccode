use crate::gateway_types::{AppState, REQUEST_ID_HEADER};
use crate::handlers::trading::strategy::summary::downstream_errors::structured_error;
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
        inference_status: aggregate
            .inference_status
            .as_ref()
            .map(from_aggregate_component)
            .unwrap_or_else(|| missing_inference_component()),
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

fn missing_inference_component() -> SummaryComponentEnvelope {
    SummaryComponentEnvelope {
        ok: false,
        status_code: 503,
        url: None,
        payload: None,
        error: Some(structured_error(
            "summary_inference_status_missing",
            "strategy aggregate summary did not include inference status",
            "gateway-aggregate",
        )),
        retry_after_ms: None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn component(payload: serde_json::Value) -> AggregateSummaryComponent {
        AggregateSummaryComponent {
            ok: true,
            status_code: 200,
            payload: Some(payload),
            error: None,
            retry_after_ms: None,
        }
    }

    #[test]
    fn build_summary_payload_maps_inference_status_when_present() {
        let aggregate = AggregateSummaryPayload {
            symbol: Some("BTCUSDT".to_string()),
            source: Some("auto".to_string()),
            recent_limit: Some(8),
            orderbook_depth: Some(10),
            signal: component(serde_json::json!({"signal": "BUY"})),
            recent_signals: component(serde_json::json!({"count": 1})),
            persistence: component(serde_json::json!({"status": "ok"})),
            matching_orderbook: component(serde_json::json!({"depth": 10})),
            inference_status: Some(component(serde_json::json!({
                "mode": "observe",
                "rollout": {
                    "configured_mode": "primary",
                    "effective_mode": "observe"
                },
                "comparison": {
                    "compared_ticks": 18,
                    "agreement_ratio": 0.5
                }
            }))),
        };
        let request = SummaryRequest {
            symbol: "BTCUSDT".to_string(),
            recent_limit: 8,
            source: "auto".to_string(),
            orderbook_depth: 10,
        };

        let payload =
            build_summary_payload_from_aggregate("https://strategy.example", &aggregate, &request);

        assert!(payload.inference_status.ok);
        assert_eq!(
            payload.inference_status.payload,
            Some(serde_json::json!({
                "mode": "observe",
                "rollout": {
                    "configured_mode": "primary",
                    "effective_mode": "observe"
                },
                "comparison": {
                    "compared_ticks": 18,
                    "agreement_ratio": 0.5
                }
            }))
        );
    }

    #[test]
    fn build_summary_payload_marks_missing_inference_status_as_component_error() {
        let aggregate = AggregateSummaryPayload {
            symbol: None,
            source: None,
            recent_limit: None,
            orderbook_depth: None,
            signal: component(serde_json::json!({"signal": "BUY"})),
            recent_signals: component(serde_json::json!({"count": 1})),
            persistence: component(serde_json::json!({"status": "ok"})),
            matching_orderbook: component(serde_json::json!({"depth": 10})),
            inference_status: None,
        };
        let request = SummaryRequest {
            symbol: "BTCUSDT".to_string(),
            recent_limit: 8,
            source: "auto".to_string(),
            orderbook_depth: 10,
        };

        let payload =
            build_summary_payload_from_aggregate("https://strategy.example", &aggregate, &request);

        assert!(!payload.inference_status.ok);
        assert_eq!(payload.inference_status.status_code, 503);
    }
}
