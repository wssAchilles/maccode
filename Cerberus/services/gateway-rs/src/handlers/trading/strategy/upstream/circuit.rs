use crate::gateway_types::AppState;
use crate::gateway_utils::current_millis;

pub(super) async fn check_circuit_open(state: &AppState) -> Option<u64> {
    if !state.strategy_upstream.circuit_enabled {
        return None;
    }
    let now_ms = current_millis();
    let mut circuit = state.strategy_upstream_circuit.write().await;
    let Some(opened_at) = circuit.opened_at_ms else {
        return None;
    };
    let elapsed = now_ms.saturating_sub(opened_at);
    if elapsed < state.strategy_upstream.circuit_open_ms {
        return Some(
            state
                .strategy_upstream
                .circuit_open_ms
                .saturating_sub(elapsed),
        );
    }

    circuit.opened_at_ms = None;
    circuit.consecutive_failures = 0;
    let mut metrics = state.metrics.write().await;
    metrics.strategy_upstream_circuit_open = false;
    metrics.strategy_upstream_circuit_opened_at = None;
    None
}

pub(super) async fn record_circuit_rejection(state: &AppState, retry_after_ms: u64) {
    let mut metrics = state.metrics.write().await;
    metrics.strategy_upstream_circuit_rejections_total += 1;
    metrics.strategy_upstream_circuit_open = true;
    metrics.strategy_upstream_last_error = Some(format!(
        "strategy upstream circuit open, retry after {retry_after_ms}ms"
    ));
}

pub(super) async fn record_success(state: &AppState) {
    if state.strategy_upstream.circuit_enabled {
        let mut circuit = state.strategy_upstream_circuit.write().await;
        circuit.consecutive_failures = 0;
        circuit.opened_at_ms = None;
        circuit.last_failure_reason = None;
    }
    let mut metrics = state.metrics.write().await;
    metrics.strategy_upstream_circuit_open = false;
    metrics.strategy_upstream_circuit_opened_at = None;
}

pub(super) async fn record_failure(state: &AppState, reason: String, trip_candidate: bool) {
    let now_ms = current_millis();
    let mut metrics = state.metrics.write().await;
    metrics.strategy_upstream_failures_total += 1;
    metrics.strategy_upstream_last_error = Some(reason.clone());
    drop(metrics);

    if !state.strategy_upstream.circuit_enabled || !trip_candidate {
        return;
    }

    let mut circuit = state.strategy_upstream_circuit.write().await;
    circuit.consecutive_failures = circuit.consecutive_failures.saturating_add(1);
    circuit.last_failure_reason = Some(reason);
    if circuit.consecutive_failures >= state.strategy_upstream.circuit_failure_threshold
        && circuit.opened_at_ms.is_none()
    {
        circuit.opened_at_ms = Some(now_ms);
        let mut metrics = state.metrics.write().await;
        metrics.strategy_upstream_circuit_open = true;
        metrics.strategy_upstream_circuit_opened_at = Some(now_ms);
    }
}
