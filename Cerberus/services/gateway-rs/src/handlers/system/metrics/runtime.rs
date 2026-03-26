use crate::gateway_types::{AppState, GatewayMetrics};
use crate::gateway_utils::current_millis;

use super::shared::latency_p95_ms;

pub(super) struct DerivedMetrics {
    pub(super) uptime_seconds: u64,
    pub(super) request_throughput_rps: f64,
    pub(super) p95_latency_ms: f64,
    pub(super) estimated_request_cost_usd: f64,
    pub(super) estimated_total_cost_usd: f64,
    pub(super) strategy_upstream_inflight: usize,
    pub(super) last_market_event_timestamp_seconds: f64,
    pub(super) last_order_event_timestamp_seconds: f64,
}

pub(super) fn derive_metrics(state: &AppState, metrics: &GatewayMetrics) -> DerivedMetrics {
    let uptime_seconds = (current_millis() / 1_000).saturating_sub(state.started_at_unix);
    let request_throughput_rps = if uptime_seconds == 0 {
        0.0
    } else {
        metrics.http_requests_total as f64 / uptime_seconds as f64
    };
    let p95_latency_ms = latency_p95_ms(&metrics.http_latency_samples_ms);
    let estimated_request_cost_usd = state.unit_request_cost_usd;
    let estimated_total_cost_usd = estimated_request_cost_usd * metrics.http_requests_total as f64;
    let strategy_upstream_inflight = state
        .strategy_upstream
        .max_inflight
        .saturating_sub(state.strategy_upstream_semaphore.available_permits());
    let last_market_event_timestamp_seconds = metrics
        .last_market_event_at
        .map(|value| value as f64 / 1_000.0)
        .unwrap_or(0.0);
    let last_order_event_timestamp_seconds = metrics
        .last_order_event_at
        .map(|value| value as f64 / 1_000.0)
        .unwrap_or(0.0);

    DerivedMetrics {
        uptime_seconds,
        request_throughput_rps,
        p95_latency_ms,
        estimated_request_cost_usd,
        estimated_total_cost_usd,
        strategy_upstream_inflight,
        last_market_event_timestamp_seconds,
        last_order_event_timestamp_seconds,
    }
}
