mod pubsub;
mod stream;
mod stream_metrics;

use std::time::Duration;

use tokio::time::sleep;
use tracing::{error, warn};

use crate::gateway_types::AppState;
use pubsub::run_order_events_pubsub_loop;
use stream::run_order_events_stream_loop;

pub(crate) fn spawn_order_events_ingest(state: AppState) {
    tokio::spawn(async move {
        loop {
            if let Err(err) = run_order_events_loop(state.clone()).await {
                error!("order events ingest failed: {err:#}");
                {
                    let mut metrics = state.metrics.write().await;
                    metrics.last_order_ingest_error = Some(err.to_string());
                }
                sleep(Duration::from_secs(2)).await;
            }
        }
    });
}

async fn run_order_events_loop(state: AppState) -> anyhow::Result<()> {
    if state.redis_url.trim().is_empty() {
        warn!("REDIS_URL empty, running without order events stream");
        sleep(Duration::from_secs(10)).await;
        return Ok(());
    }

    if state.order_event_stream.enabled {
        match run_order_events_stream_loop(&state).await {
            Ok(()) => return Ok(()),
            Err(err) => {
                if state.order_event_stream.legacy_pubsub_fallback {
                    warn!("redis stream ingest failed, fallback to pubsub mode: {err:#}");
                    record_stream_fallback_failure(&state, &err.to_string()).await;
                } else {
                    record_stream_hard_failure(&state, &err.to_string()).await;
                    return Err(err);
                }
            }
        }
    }

    run_order_events_pubsub_loop(&state).await
}

async fn record_stream_fallback_failure(state: &AppState, reason: &str) {
    let mut metrics = state.metrics.write().await;
    metrics.order_stream_read_failures += 1;
    metrics.order_stream_fallbacks += 1;
    metrics.order_stream_consecutive_failures = 0;
    metrics.last_order_stream_retry_backoff_ms = None;
    metrics.last_order_ingest_error = Some(reason.to_string());
}

async fn record_stream_hard_failure(state: &AppState, reason: &str) {
    let mut metrics = state.metrics.write().await;
    metrics.order_stream_read_failures += 1;
    metrics.last_order_ingest_error = Some(reason.to_string());
}
