use crate::gateway_types::{AppState, GatewayMetrics};

use super::json_sections::{
    insert_http_and_cost_fields, insert_identity_fields, insert_market_ingest_fields,
    insert_order_stream_fields, insert_strategy_summary_fields, insert_strategy_upstream_fields,
};
use super::runtime::derive_metrics;

pub(super) fn build_metrics_json(
    state: &AppState,
    metrics: &GatewayMetrics,
    tracked_symbols: usize,
) -> serde_json::Value {
    let derived = derive_metrics(state, metrics);
    let mut data = serde_json::Map::new();
    insert_identity_fields(&mut data, derived.uptime_seconds);
    insert_market_ingest_fields(&mut data, state, metrics, tracked_symbols);
    insert_http_and_cost_fields(&mut data, metrics, &derived);
    insert_order_stream_fields(&mut data, metrics);
    insert_strategy_upstream_fields(&mut data, metrics, derived.strategy_upstream_inflight);
    insert_strategy_summary_fields(&mut data, metrics);
    serde_json::Value::Object(data)
}
