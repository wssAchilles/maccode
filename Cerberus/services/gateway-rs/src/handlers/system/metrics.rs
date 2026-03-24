use std::fmt::Write as _;

use crate::gateway_types::{AppState, GatewayMetrics, SERVICE_NAME, SERVICE_VERSION};
use crate::gateway_utils::{current_millis, escape_prometheus_label};

pub(super) fn build_metrics_json(
    state: &AppState,
    metrics: &GatewayMetrics,
    tracked_symbols: usize,
) -> serde_json::Value {
    serde_json::json!({
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "uptime_seconds": (current_millis() / 1_000).saturating_sub(state.started_at_unix),
        "market_events": metrics.market_events,
        "order_events": metrics.order_events,
        "market_redis_publish_failures": metrics.market_redis_publish_failures,
        "last_market_event_at": metrics.last_market_event_at,
        "last_order_event_at": metrics.last_order_event_at,
        "last_market_ingest_error": metrics.last_market_ingest_error,
        "last_order_ingest_error": metrics.last_order_ingest_error,
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

    body
}
