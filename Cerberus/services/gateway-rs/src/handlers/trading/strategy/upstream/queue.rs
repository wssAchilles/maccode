use std::time::Duration;

use tokio::time::timeout;

use crate::gateway_types::AppState;

use super::error::StrategyUpstreamError;
use super::metrics::record_queue_rejection;

pub(super) async fn acquire_upstream_slot(
    state: &AppState,
) -> Result<tokio::sync::OwnedSemaphorePermit, StrategyUpstreamError> {
    match timeout(
        Duration::from_millis(state.strategy_upstream.queue_timeout_ms),
        state.strategy_upstream_semaphore.clone().acquire_owned(),
    )
    .await
    {
        Ok(Ok(permit)) => Ok(permit),
        Ok(Err(_)) => {
            let waited_ms = state.strategy_upstream.queue_timeout_ms;
            record_queue_rejection(state, "strategy upstream semaphore closed".to_string()).await;
            Err(StrategyUpstreamError::QueueSaturated { waited_ms })
        }
        Err(_) => {
            let waited_ms = state.strategy_upstream.queue_timeout_ms;
            record_queue_rejection(
                state,
                format!("strategy upstream queue timeout after {waited_ms}ms"),
            )
            .await;
            Err(StrategyUpstreamError::QueueSaturated { waited_ms })
        }
    }
}
