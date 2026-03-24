use axum::http::StatusCode;

use crate::gateway_types::{AppState, GatewayMetrics, SERVICE_NAME};
use crate::gateway_utils::current_millis;

pub(super) fn build_ready_payload(
    state: &AppState,
    metrics: &GatewayMetrics,
) -> (StatusCode, serde_json::Value) {
    let mut reasons = Vec::<String>::new();

    if state.redis_url.trim().is_empty() {
        reasons.push("redis_url_missing".to_string());
    }
    if metrics.last_market_ingest_error.is_some() {
        reasons.push("market_ingest_error".to_string());
    }
    if metrics.last_order_ingest_error.is_some() {
        reasons.push("order_events_ingest_error".to_string());
    }

    let ready = reasons.is_empty();
    let status = if ready {
        StatusCode::OK
    } else {
        StatusCode::SERVICE_UNAVAILABLE
    };

    (
        status,
        serde_json::json!({
            "ready": ready,
            "service": SERVICE_NAME,
            "reasons": reasons,
            "uptime_seconds": (current_millis() / 1_000).saturating_sub(state.started_at_unix),
            "metrics": {
                "market_events": metrics.market_events,
                "order_events": metrics.order_events,
                "last_market_event_at": metrics.last_market_event_at,
                "last_order_event_at": metrics.last_order_event_at,
                "last_market_ingest_error": metrics.last_market_ingest_error,
                "last_order_ingest_error": metrics.last_order_ingest_error
            }
        }),
    )
}
