use crate::gateway_types::{AppState, GatewayMetrics, SERVICE_NAME, SERVICE_VERSION};

use super::runtime::DerivedMetrics;

pub(super) fn insert_identity_fields(
    data: &mut serde_json::Map<String, serde_json::Value>,
    uptime_seconds: u64,
) {
    data.insert("service".to_string(), serde_json::json!(SERVICE_NAME));
    data.insert("version".to_string(), serde_json::json!(SERVICE_VERSION));
    data.insert(
        "uptime_seconds".to_string(),
        serde_json::json!(uptime_seconds),
    );
}

pub(super) fn insert_market_ingest_fields(
    data: &mut serde_json::Map<String, serde_json::Value>,
    state: &AppState,
    metrics: &GatewayMetrics,
    tracked_symbols: usize,
) {
    data.insert(
        "market_events".to_string(),
        serde_json::json!(metrics.market_events),
    );
    data.insert(
        "order_events".to_string(),
        serde_json::json!(metrics.order_events),
    );
    data.insert(
        "market_redis_publish_failures".to_string(),
        serde_json::json!(metrics.market_redis_publish_failures),
    );
    data.insert(
        "market_stream_events".to_string(),
        serde_json::json!(metrics.market_stream_events),
    );
    data.insert(
        "market_stream_publish_failures".to_string(),
        serde_json::json!(metrics.market_stream_publish_failures),
    );
    data.insert(
        "last_market_stream_id".to_string(),
        serde_json::json!(metrics.last_market_stream_id),
    );
    data.insert(
        "last_market_event_at".to_string(),
        serde_json::json!(metrics.last_market_event_at),
    );
    data.insert(
        "last_order_event_at".to_string(),
        serde_json::json!(metrics.last_order_event_at),
    );
    data.insert(
        "last_market_ingest_error".to_string(),
        serde_json::json!(metrics.last_market_ingest_error),
    );
    data.insert(
        "last_order_ingest_error".to_string(),
        serde_json::json!(metrics.last_order_ingest_error),
    );
    data.insert(
        "configured_market_symbols".to_string(),
        serde_json::json!(state.market_symbols),
    );
    data.insert(
        "tracked_market_symbols".to_string(),
        serde_json::json!(tracked_symbols),
    );
}

pub(super) fn insert_http_and_cost_fields(
    data: &mut serde_json::Map<String, serde_json::Value>,
    metrics: &GatewayMetrics,
    derived: &DerivedMetrics,
) {
    data.insert(
        "http_requests_total".to_string(),
        serde_json::json!(metrics.http_requests_total),
    );
    data.insert(
        "http_requests_4xx".to_string(),
        serde_json::json!(metrics.http_requests_4xx),
    );
    data.insert(
        "http_requests_5xx".to_string(),
        serde_json::json!(metrics.http_requests_5xx),
    );
    data.insert(
        "http_latency_p95_ms".to_string(),
        serde_json::json!(derived.p95_latency_ms),
    );
    data.insert(
        "http_last_latency_ms".to_string(),
        serde_json::json!(metrics.last_http_latency_ms),
    );
    data.insert(
        "request_throughput_rps".to_string(),
        serde_json::json!(derived.request_throughput_rps),
    );
    data.insert(
        "estimated_request_cost_usd".to_string(),
        serde_json::json!(derived.estimated_request_cost_usd),
    );
    data.insert(
        "estimated_total_cost_usd".to_string(),
        serde_json::json!(derived.estimated_total_cost_usd),
    );
}

pub(super) fn insert_order_stream_fields(
    data: &mut serde_json::Map<String, serde_json::Value>,
    metrics: &GatewayMetrics,
) {
    data.insert(
        "order_stream_events".to_string(),
        serde_json::json!(metrics.order_stream_events),
    );
    data.insert(
        "order_stream_ack_failures".to_string(),
        serde_json::json!(metrics.order_stream_ack_failures),
    );
    data.insert(
        "order_stream_read_failures".to_string(),
        serde_json::json!(metrics.order_stream_read_failures),
    );
    data.insert(
        "order_stream_retry_attempts".to_string(),
        serde_json::json!(metrics.order_stream_retry_attempts),
    );
    data.insert(
        "order_stream_fallbacks".to_string(),
        serde_json::json!(metrics.order_stream_fallbacks),
    );
    data.insert(
        "order_stream_consecutive_failures".to_string(),
        serde_json::json!(metrics.order_stream_consecutive_failures),
    );
    data.insert(
        "last_order_stream_retry_backoff_ms".to_string(),
        serde_json::json!(metrics.last_order_stream_retry_backoff_ms),
    );
    data.insert(
        "last_order_stream_id".to_string(),
        serde_json::json!(metrics.last_order_stream_id),
    );
    data.insert(
        "order_stream_pending".to_string(),
        serde_json::json!(metrics.order_stream_pending),
    );
    data.insert(
        "order_stream_lag".to_string(),
        serde_json::json!(metrics.order_stream_lag),
    );
    data.insert(
        "order_stream_reclaim_attempts".to_string(),
        serde_json::json!(metrics.order_stream_reclaim_attempts),
    );
    data.insert(
        "order_stream_reclaimed_events".to_string(),
        serde_json::json!(metrics.order_stream_reclaimed_events),
    );
    data.insert(
        "order_stream_reclaim_failures".to_string(),
        serde_json::json!(metrics.order_stream_reclaim_failures),
    );
    data.insert(
        "order_stream_poisoned_events".to_string(),
        serde_json::json!(metrics.order_stream_poisoned_events),
    );
    data.insert(
        "last_order_stream_reclaim_at".to_string(),
        serde_json::json!(metrics.last_order_stream_reclaim_at),
    );
    data.insert(
        "last_order_stream_poison_id".to_string(),
        serde_json::json!(metrics.last_order_stream_poison_id),
    );
}

pub(super) fn insert_strategy_upstream_fields(
    data: &mut serde_json::Map<String, serde_json::Value>,
    metrics: &GatewayMetrics,
    strategy_upstream_inflight: usize,
) {
    data.insert(
        "strategy_upstream_requests_total".to_string(),
        serde_json::json!(metrics.strategy_upstream_requests_total),
    );
    data.insert(
        "strategy_upstream_failures_total".to_string(),
        serde_json::json!(metrics.strategy_upstream_failures_total),
    );
    data.insert(
        "strategy_upstream_auth_failures_total".to_string(),
        serde_json::json!(metrics.strategy_upstream_auth_failures_total),
    );
    data.insert(
        "strategy_upstream_circuit_rejections_total".to_string(),
        serde_json::json!(metrics.strategy_upstream_circuit_rejections_total),
    );
    data.insert(
        "strategy_upstream_queue_rejections_total".to_string(),
        serde_json::json!(metrics.strategy_upstream_queue_rejections_total),
    );
    data.insert(
        "strategy_upstream_circuit_open".to_string(),
        serde_json::json!(metrics.strategy_upstream_circuit_open),
    );
    data.insert(
        "strategy_upstream_circuit_opened_at".to_string(),
        serde_json::json!(metrics.strategy_upstream_circuit_opened_at),
    );
    data.insert(
        "strategy_upstream_last_error".to_string(),
        serde_json::json!(metrics.strategy_upstream_last_error),
    );
    data.insert(
        "strategy_upstream_inflight".to_string(),
        serde_json::json!(strategy_upstream_inflight),
    );
}

pub(super) fn insert_strategy_summary_fields(
    data: &mut serde_json::Map<String, serde_json::Value>,
    metrics: &GatewayMetrics,
) {
    data.insert(
        "strategy_summary_cache_hits".to_string(),
        serde_json::json!(metrics.strategy_summary_cache_hits),
    );
    data.insert(
        "strategy_summary_cache_misses".to_string(),
        serde_json::json!(metrics.strategy_summary_cache_misses),
    );
    data.insert(
        "strategy_summary_coalesced_waits".to_string(),
        serde_json::json!(metrics.strategy_summary_coalesced_waits),
    );
}
