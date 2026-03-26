use crate::gateway_types::{AppState, GatewayMetrics};
use crate::gateway_utils::current_millis;

#[derive(Clone, Debug)]
pub(super) struct ReadinessContext {
    pub(super) uptime_seconds: u64,
    pub(super) market_staleness_ms: Option<u64>,
}

pub(super) fn build_readiness_context(
    state: &AppState,
    metrics: &GatewayMetrics,
) -> ReadinessContext {
    let now_ms = current_millis();
    ReadinessContext {
        uptime_seconds: (now_ms / 1_000).saturating_sub(state.started_at_unix),
        market_staleness_ms: metrics
            .last_market_event_at
            .map(|last| now_ms.saturating_sub(last)),
    }
}
