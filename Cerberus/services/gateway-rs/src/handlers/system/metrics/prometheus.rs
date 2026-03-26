use std::fmt::Write as _;

use crate::gateway_types::{AppState, GatewayMetrics, SERVICE_NAME, SERVICE_VERSION};
use crate::gateway_utils::{current_millis, escape_prometheus_label};

use super::shared::latency_p95_ms;

pub(super) fn build_prometheus_body(
    state: &AppState,
    metrics: &GatewayMetrics,
    tracked_symbols: usize,
) -> String {
    let now_seconds = current_millis() / 1_000;
    let uptime_seconds = now_seconds.saturating_sub(state.started_at_unix);
    let market_last = metrics
        .last_market_event_at
        .map(|ts| ts as f64 / 1_000.0)
        .unwrap_or(0.0);
    let order_last = metrics
        .last_order_event_at
        .map(|ts| ts as f64 / 1_000.0)
        .unwrap_or(0.0);
    let p95_latency_ms = latency_p95_ms(&metrics.http_latency_samples_ms);
    let request_throughput_rps = if uptime_seconds == 0 {
        0.0
    } else {
        metrics.http_requests_total as f64 / uptime_seconds as f64
    };
    let total_cost_usd = state.unit_request_cost_usd * metrics.http_requests_total as f64;
    let strategy_upstream_inflight = state
        .strategy_upstream
        .max_inflight
        .saturating_sub(state.strategy_upstream_semaphore.available_permits());

    let mut body = String::with_capacity(1_024);
    let _ = writeln!(body, "# HELP cerberus_gateway_up Gateway process health.");
    let _ = writeln!(body, "# TYPE cerberus_gateway_up gauge");
    let _ = writeln!(body, "cerberus_gateway_up 1");
    let _ = writeln!(
        body,
        "cerberus_gateway_build_info{{service=\"{}\",version=\"{}\"}} 1",
        escape_prometheus_label(SERVICE_NAME),
        escape_prometheus_label(SERVICE_VERSION)
    );
    let _ = writeln!(body, "cerberus_gateway_uptime_seconds {}", uptime_seconds);
    let _ = writeln!(
        body,
        "cerberus_gateway_market_events_total {}",
        metrics.market_events
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_order_events_total {}",
        metrics.order_events
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_market_redis_publish_failures_total {}",
        metrics.market_redis_publish_failures
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_market_stream_events_total {}",
        metrics.market_stream_events
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_market_stream_publish_failures_total {}",
        metrics.market_stream_publish_failures
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_last_market_event_timestamp_seconds {}",
        market_last
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_last_order_event_timestamp_seconds {}",
        order_last
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_market_ingest_error {}",
        if metrics.last_market_ingest_error.is_some() {
            1
        } else {
            0
        }
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_order_ingest_error {}",
        if metrics.last_order_ingest_error.is_some() {
            1
        } else {
            0
        }
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_market_symbols_configured {}",
        state.market_symbols.len()
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_market_symbols_tracked {}",
        tracked_symbols
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_http_requests_total {}",
        metrics.http_requests_total
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_http_requests_4xx_total {}",
        metrics.http_requests_4xx
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_http_requests_5xx_total {}",
        metrics.http_requests_5xx
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_http_latency_p95_ms {}",
        p95_latency_ms
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_http_request_throughput_rps {:.6}",
        request_throughput_rps
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_unit_request_cost_usd {:.8}",
        state.unit_request_cost_usd
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_total_estimated_cost_usd {:.8}",
        total_cost_usd
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_order_stream_events_total {}",
        metrics.order_stream_events
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_order_stream_ack_failures_total {}",
        metrics.order_stream_ack_failures
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_order_stream_read_failures_total {}",
        metrics.order_stream_read_failures
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_order_stream_retry_attempts_total {}",
        metrics.order_stream_retry_attempts
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_order_stream_fallbacks_total {}",
        metrics.order_stream_fallbacks
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_order_stream_consecutive_failures {}",
        metrics.order_stream_consecutive_failures
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_order_stream_last_retry_backoff_ms {}",
        metrics.last_order_stream_retry_backoff_ms.unwrap_or(0)
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_order_stream_pending {}",
        metrics.order_stream_pending
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_order_stream_lag {}",
        metrics.order_stream_lag
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_order_stream_reclaim_attempts_total {}",
        metrics.order_stream_reclaim_attempts
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_order_stream_reclaimed_events_total {}",
        metrics.order_stream_reclaimed_events
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_order_stream_reclaim_failures_total {}",
        metrics.order_stream_reclaim_failures
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_order_stream_poisoned_events_total {}",
        metrics.order_stream_poisoned_events
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_order_stream_last_reclaim_at_seconds {}",
        metrics
            .last_order_stream_reclaim_at
            .map(|value| value as f64 / 1_000.0)
            .unwrap_or(0.0)
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_strategy_upstream_requests_total {}",
        metrics.strategy_upstream_requests_total
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_strategy_upstream_failures_total {}",
        metrics.strategy_upstream_failures_total
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_strategy_upstream_auth_failures_total {}",
        metrics.strategy_upstream_auth_failures_total
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_strategy_upstream_circuit_rejections_total {}",
        metrics.strategy_upstream_circuit_rejections_total
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_strategy_upstream_queue_rejections_total {}",
        metrics.strategy_upstream_queue_rejections_total
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_strategy_upstream_circuit_open {}",
        if metrics.strategy_upstream_circuit_open {
            1
        } else {
            0
        }
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_strategy_upstream_inflight {}",
        strategy_upstream_inflight
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_strategy_summary_cache_hits_total {}",
        metrics.strategy_summary_cache_hits
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_strategy_summary_cache_misses_total {}",
        metrics.strategy_summary_cache_misses
    );
    let _ = writeln!(
        body,
        "cerberus_gateway_strategy_summary_coalesced_waits_total {}",
        metrics.strategy_summary_coalesced_waits
    );

    body
}
