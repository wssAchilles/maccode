use crate::gateway_types::{AppState, GatewayMetrics};

use super::prometheus_sections::{
    write_http_and_cost_metrics, write_identity_metrics, write_market_ingest_metrics,
    write_order_stream_metrics, write_strategy_summary_metrics, write_strategy_upstream_metrics,
};
use super::runtime::derive_metrics;

pub(super) fn build_prometheus_body(
    state: &AppState,
    metrics: &GatewayMetrics,
    tracked_symbols: usize,
) -> String {
    let derived = derive_metrics(state, metrics);
    let mut body = String::with_capacity(1_024);
    write_identity_metrics(&mut body, derived.uptime_seconds);
    write_market_ingest_metrics(&mut body, state, metrics, &derived, tracked_symbols);
    write_http_and_cost_metrics(&mut body, state, metrics, &derived);
    write_order_stream_metrics(&mut body, metrics);
    write_strategy_upstream_metrics(&mut body, metrics, derived.strategy_upstream_inflight);
    write_strategy_summary_metrics(&mut body, metrics);
    body
}
