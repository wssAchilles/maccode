use std::fmt::Write as _;

use crate::gateway_types::{AppState, GatewayMetrics, SERVICE_NAME, SERVICE_VERSION};
use crate::gateway_utils::{current_millis, escape_prometheus_label};

pub(super) fn build_metrics_json(
    state: &AppState,
    metrics: &GatewayMetrics,
    tracked_symbols: usize,
) -> serde_json::Value {
    let uptime_seconds = (current_millis() / 1_000).saturating_sub(state.started_at_unix);
    let request_throughput_rps = if uptime_seconds == 0 {
        0.0
    } else {
        metrics.http_requests_total as f64 / uptime_seconds as f64
    };
    let p95_latency_ms = latency_p95_ms(&metrics.http_latency_samples_ms);
    let estimated_request_cost_usd = state.unit_request_cost_usd;
    serde_json::json!({
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "uptime_seconds": uptime_seconds,
        "market_events": metrics.market_events,
        "order_events": metrics.order_events,
        "market_redis_publish_failures": metrics.market_redis_publish_failures,
        "market_stream_events": metrics.market_stream_events,
        "market_stream_publish_failures": metrics.market_stream_publish_failures,
        "last_market_stream_id": metrics.last_market_stream_id,
        "last_market_event_at": metrics.last_market_event_at,
        "last_order_event_at": metrics.last_order_event_at,
        "last_market_ingest_error": metrics.last_market_ingest_error,
        "last_order_ingest_error": metrics.last_order_ingest_error,
        "http_requests_total": metrics.http_requests_total,
        "http_requests_4xx": metrics.http_requests_4xx,
        "http_requests_5xx": metrics.http_requests_5xx,
        "http_latency_p95_ms": p95_latency_ms,
        "http_last_latency_ms": metrics.last_http_latency_ms,
        "request_throughput_rps": request_throughput_rps,
        "estimated_request_cost_usd": estimated_request_cost_usd,
        "estimated_total_cost_usd": estimated_request_cost_usd * metrics.http_requests_total as f64,
        "order_stream_events": metrics.order_stream_events,
        "order_stream_ack_failures": metrics.order_stream_ack_failures,
        "order_stream_read_failures": metrics.order_stream_read_failures,
        "order_stream_retry_attempts": metrics.order_stream_retry_attempts,
        "order_stream_fallbacks": metrics.order_stream_fallbacks,
        "order_stream_consecutive_failures": metrics.order_stream_consecutive_failures,
        "last_order_stream_retry_backoff_ms": metrics.last_order_stream_retry_backoff_ms,
        "last_order_stream_id": metrics.last_order_stream_id,
        "configured_market_symbols": state.market_symbols,
        "tracked_market_symbols": tracked_symbols
    })
}

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

    body
}

fn latency_p95_ms(samples: &std::collections::VecDeque<u64>) -> f64 {
    if samples.is_empty() {
        return 0.0;
    }
    let mut values = samples.iter().copied().collect::<Vec<_>>();
    values.sort_unstable();
    let idx = ((values.len() as f64) * 0.95).ceil() as usize;
    let pos = idx.saturating_sub(1).min(values.len() - 1);
    values[pos] as f64
}
