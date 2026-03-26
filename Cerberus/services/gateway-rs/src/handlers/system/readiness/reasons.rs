use crate::gateway_types::{AppState, GatewayMetrics};
use crate::gateway_utils::current_millis;

use super::context::ReadinessContext;

pub(super) fn collect_readiness_reasons(
    state: &AppState,
    metrics: &GatewayMetrics,
    context: &ReadinessContext,
) -> Vec<String> {
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
    if state.order_event_stream.pending_warn_threshold > 0
        && metrics.order_stream_pending > state.order_event_stream.pending_warn_threshold as u64
    {
        reasons.push("order_stream_pending_high".to_string());
    }
    if state.order_event_stream.lag_warn_threshold > 0
        && metrics.order_stream_lag > state.order_event_stream.lag_warn_threshold as u64
    {
        reasons.push("order_stream_lag_high".to_string());
    }
    if metrics.strategy_upstream_circuit_open {
        reasons.push("strategy_upstream_circuit_open".to_string());
    }

    append_market_readiness_reason(state, context, &mut reasons);
    reasons
}

fn append_market_readiness_reason(
    state: &AppState,
    context: &ReadinessContext,
    reasons: &mut Vec<String>,
) {
    if state.ready_max_market_staleness_ms == 0 {
        return;
    }

    match context.market_staleness_ms {
        Some(staleness) if staleness > state.ready_max_market_staleness_ms => {
            reasons.push("market_data_stale".to_string());
        }
        None => {
            let uptime_ms =
                current_millis().saturating_sub(state.started_at_unix.saturating_mul(1_000));
            if uptime_ms > state.ready_max_market_staleness_ms {
                reasons.push("market_data_missing".to_string());
            }
        }
        _ => {}
    }
}
