use crate::gateway_types::AppState;
use crate::gateway_utils::current_millis;

pub(super) async fn set_backlog_metrics(state: &AppState, pending: u64, lag: u64) {
    let mut metrics = state.metrics.write().await;
    metrics.order_stream_pending = pending;
    metrics.order_stream_lag = lag;
}

pub(super) async fn mark_reclaim_attempt(state: &AppState) {
    let mut metrics = state.metrics.write().await;
    metrics.order_stream_reclaim_attempts += 1;
    metrics.last_order_stream_reclaim_at = Some(current_millis());
}

pub(super) async fn add_reclaimed_events(state: &AppState, reclaimed_events: u64) {
    let mut metrics = state.metrics.write().await;
    metrics.order_stream_reclaimed_events += reclaimed_events;
}

pub(super) async fn mark_poisoned_event(state: &AppState, stream_id: &str) {
    let mut metrics = state.metrics.write().await;
    metrics.order_stream_poisoned_events += 1;
    metrics.last_order_stream_poison_id = Some(stream_id.to_string());
}

pub(super) async fn mark_ack_result(state: &AppState, stream_ids: &[String], acked: usize) {
    let mut metrics = state.metrics.write().await;
    metrics.order_stream_events += stream_ids.len() as u64;
    metrics.last_order_stream_id = stream_ids.last().cloned();
    if acked < stream_ids.len() {
        metrics.order_stream_ack_failures += (stream_ids.len() - acked) as u64;
    }
    metrics.last_order_ingest_error = None;
}

pub(super) async fn record_reclaim_failure(state: &AppState, reason: &str) {
    let mut metrics = state.metrics.write().await;
    metrics.order_stream_reclaim_failures += 1;
    metrics.last_order_ingest_error = Some(reason.to_string());
}

pub(super) async fn clear_order_ingest_error(state: &AppState) {
    let mut metrics = state.metrics.write().await;
    metrics.last_order_ingest_error = None;
}

pub(super) async fn record_stream_retry_attempt(
    state: &AppState,
    consecutive_failures: usize,
    backoff_ms: u64,
    reason: &str,
) {
    let mut metrics = state.metrics.write().await;
    metrics.order_stream_retry_attempts += 1;
    metrics.order_stream_consecutive_failures = consecutive_failures as u64;
    metrics.last_order_stream_retry_backoff_ms = Some(backoff_ms);
    metrics.last_order_ingest_error = Some(reason.to_string());
}

pub(super) async fn mark_stream_iteration_success(state: &AppState) {
    let mut metrics = state.metrics.write().await;
    metrics.order_stream_consecutive_failures = 0;
    metrics.last_order_stream_retry_backoff_ms = None;
}
