mod json;
mod prometheus;
mod shared;

use crate::gateway_types::{AppState, GatewayMetrics};

pub(super) fn build_metrics_json(
    state: &AppState,
    metrics: &GatewayMetrics,
    tracked_symbols: usize,
) -> serde_json::Value {
    json::build_metrics_json(state, metrics, tracked_symbols)
}

pub(super) fn build_prometheus_body(
    state: &AppState,
    metrics: &GatewayMetrics,
    tracked_symbols: usize,
) -> String {
    prometheus::build_prometheus_body(state, metrics, tracked_symbols)
}
