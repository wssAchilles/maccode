use crate::gateway_types::AppState;

pub(super) async fn increment_upstream_requests(state: &AppState) {
    let mut metrics = state.metrics.write().await;
    metrics.strategy_upstream_requests_total += 1;
}

pub(super) async fn record_auth_failure(state: &AppState, reason: String) {
    let mut metrics = state.metrics.write().await;
    metrics.strategy_upstream_auth_failures_total += 1;
    metrics.strategy_upstream_last_error = Some(reason);
}

pub(super) async fn record_queue_rejection(state: &AppState, reason: String) {
    let mut metrics = state.metrics.write().await;
    metrics.strategy_upstream_queue_rejections_total += 1;
    metrics.strategy_upstream_last_error = Some(reason);
}
