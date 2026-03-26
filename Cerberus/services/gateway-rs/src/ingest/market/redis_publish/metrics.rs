use crate::gateway_types::AppState;

pub(super) async fn record_market_stream_success(state: &AppState, stream_id: String) {
    let mut metrics = state.metrics.write().await;
    metrics.market_stream_events += 1;
    metrics.last_market_stream_id = Some(stream_id);
}

pub(super) async fn increment_redis_publish_failure(state: &AppState) {
    let mut metrics = state.metrics.write().await;
    metrics.market_redis_publish_failures += 1;
}

pub(super) async fn increment_market_stream_publish_failure(state: &AppState) {
    let mut metrics = state.metrics.write().await;
    metrics.market_stream_publish_failures += 1;
    metrics.market_redis_publish_failures += 1;
}
