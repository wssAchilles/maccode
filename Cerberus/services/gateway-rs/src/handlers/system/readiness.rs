use axum::http::StatusCode;

use crate::gateway_types::{AppState, GatewayMetrics, SERVICE_NAME};
use crate::gateway_utils::current_millis;

pub(super) fn build_ready_payload(
    state: &AppState,
    metrics: &GatewayMetrics,
) -> (StatusCode, serde_json::Value) {
    let mut reasons = Vec::<String>::new();
    let now_ms = current_millis();
    let uptime_seconds = (now_ms / 1_000).saturating_sub(state.started_at_unix);
    let market_staleness_ms = metrics
        .last_market_event_at
        .map(|last| now_ms.saturating_sub(last));

    if state.redis_url.trim().is_empty() {
        reasons.push("redis_url_missing".to_string());
    }
    if metrics.last_market_ingest_error.is_some() {
        reasons.push("market_ingest_error".to_string());
    }
    if metrics.last_order_ingest_error.is_some() {
        reasons.push("order_events_ingest_error".to_string());
    }
    if state.market_event_stream.enabled
        && !state.market_event_stream.publish_legacy_pubsub
        && metrics.market_stream_publish_failures > 0
    {
        reasons.push("market_stream_publish_error".to_string());
    }
    if state.jwt_auth.effective_required() && state.jwt_auth.hs256_secret.is_none() {
        reasons.push("jwt_secret_missing".to_string());
    }
    if state.firebase_auth.required && state.firebase_auth.web_api_key.is_none() {
        reasons.push("firebase_web_api_key_missing".to_string());
    }
    if state.strategy_internal_auth.enabled && state.strategy_internal_auth.audience.is_none() {
        reasons.push("strategy_internal_auth_audience_missing".to_string());
    }
    if state.order_event_stream.enabled
        && metrics.order_stream_consecutive_failures
            > state.order_event_stream.max_retries_before_fallback as u64
    {
        reasons.push("order_stream_unstable".to_string());
    }
    if state.ready_max_market_staleness_ms > 0 {
        match market_staleness_ms {
            Some(staleness) if staleness > state.ready_max_market_staleness_ms => {
                reasons.push("market_data_stale".to_string());
            }
            None => {
                let uptime_ms = now_ms.saturating_sub(state.started_at_unix.saturating_mul(1_000));
                if uptime_ms > state.ready_max_market_staleness_ms {
                    reasons.push("market_data_missing".to_string());
                }
            }
            _ => {}
        }
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
            "uptime_seconds": uptime_seconds,
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
                "market_staleness_ms": market_staleness_ms,
                "last_order_event_at": metrics.last_order_event_at,
                "last_market_ingest_error": metrics.last_market_ingest_error,
                "last_order_ingest_error": metrics.last_order_ingest_error,
                "order_stream_consecutive_failures": metrics.order_stream_consecutive_failures,
                "order_stream_fallbacks": metrics.order_stream_fallbacks
            },
            "security": {
                "jwt_required": state.jwt_auth.effective_required(),
                "firebase_auth_required": state.firebase_auth.required,
                "strategy_internal_auth_enabled": state.strategy_internal_auth.enabled,
                "strategy_internal_auth_audience_configured": state.strategy_internal_auth.audience.is_some()
            }
        }),
    )
}
