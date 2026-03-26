use crate::gateway_types::{AppState, GatewayMetrics, SERVICE_NAME};

use super::context::ReadinessContext;

pub(super) fn build_readiness_payload(
    state: &AppState,
    metrics: &GatewayMetrics,
    context: &ReadinessContext,
    reasons: Vec<String>,
    ready: bool,
) -> serde_json::Value {
    serde_json::json!({
        "ready": ready,
        "service": SERVICE_NAME,
        "reasons": reasons,
        "uptime_seconds": context.uptime_seconds,
        "ready_config": {
            "max_market_staleness_ms": state.ready_max_market_staleness_ms
        },
        "metrics": {
            "market_events": metrics.market_events,
            "order_events": metrics.order_events,
            "market_stream_events": metrics.market_stream_events,
            "market_stream_publish_failures": metrics.market_stream_publish_failures,
            "last_market_stream_id": metrics.last_market_stream_id,
            "last_market_event_at": metrics.last_market_event_at,
            "market_staleness_ms": context.market_staleness_ms,
            "last_order_event_at": metrics.last_order_event_at,
            "last_market_ingest_error": metrics.last_market_ingest_error,
            "last_order_ingest_error": metrics.last_order_ingest_error,
            "order_stream_consecutive_failures": metrics.order_stream_consecutive_failures,
            "order_stream_fallbacks": metrics.order_stream_fallbacks,
            "order_stream_pending": metrics.order_stream_pending,
            "order_stream_lag": metrics.order_stream_lag,
            "order_stream_reclaim_attempts": metrics.order_stream_reclaim_attempts,
            "order_stream_reclaimed_events": metrics.order_stream_reclaimed_events,
            "order_stream_reclaim_failures": metrics.order_stream_reclaim_failures,
            "order_stream_poisoned_events": metrics.order_stream_poisoned_events,
            "last_order_stream_reclaim_at": metrics.last_order_stream_reclaim_at,
            "last_order_stream_poison_id": metrics.last_order_stream_poison_id,
            "strategy_upstream_circuit_open": metrics.strategy_upstream_circuit_open,
            "strategy_upstream_circuit_opened_at": metrics.strategy_upstream_circuit_opened_at,
            "strategy_upstream_last_error": metrics.strategy_upstream_last_error
        },
        "security": {
            "jwt_required": state.jwt_auth.effective_required(),
            "firebase_auth_required": state.firebase_auth.required,
            "strategy_internal_auth_enabled": state.strategy_internal_auth.enabled,
            "strategy_internal_auth_audience_configured": state.strategy_internal_auth.audience.is_some()
        }
    })
}
