mod stream_group;
mod stream_io;
mod stream_payload;
mod stream_processing;
mod stream_reclaim;

use std::time::Duration;

use anyhow::Context;
use redis::aio::MultiplexedConnection;
use tokio::time::sleep;
use tracing::info;

use crate::gateway_types::{AppState, OrderEventsStreamConfig};
use crate::gateway_utils::current_millis;

use super::stream_metrics::{
    clear_order_ingest_error, mark_stream_iteration_success, record_reclaim_failure,
    record_stream_retry_attempt,
};
use stream_group::{ensure_stream_consumer_group, replay_pending_entries};
use stream_io::read_stream_entries;
use stream_processing::process_stream_batch;
use stream_reclaim::{reclaim_stuck_stream_entries, refresh_stream_backlog_metrics};

pub(super) async fn run_order_events_stream_loop(state: &AppState) -> anyhow::Result<()> {
    let client = redis::Client::open(state.redis_url.as_str()).context("invalid redis url")?;
    let mut conn = client
        .get_multiplexed_async_connection()
        .await
        .context("redis stream connection failed")?;

    ensure_stream_consumer_group(&mut conn, &state.order_event_stream).await?;
    clear_order_ingest_error(state).await;

    replay_pending_entries(state, &mut conn).await?;
    info!(
        "consuming order events stream={} group={} consumer={}",
        state.order_event_stream.stream_key,
        state.order_event_stream.consumer_group,
        state.order_event_stream.consumer_name
    );
    stream_consume_loop(state, &mut conn).await
}

async fn stream_consume_loop(
    state: &AppState,
    conn: &mut MultiplexedConnection,
) -> anyhow::Result<()> {
    let mut consecutive_failures = 0usize;
    let mut last_maintenance_at_ms = 0u64;
    loop {
        let cfg = &state.order_event_stream;
        if should_run_stream_maintenance(cfg, last_maintenance_at_ms) {
            if let Err(err) = run_stream_maintenance(state, conn).await {
                record_reclaim_failure(state, &err.to_string()).await;
            }
            last_maintenance_at_ms = current_millis();
        }
        let step_result = async {
            let entries =
                read_stream_entries(conn, cfg, ">", cfg.read_batch_size, cfg.read_block_ms).await?;
            if entries.is_empty() {
                return Ok(());
            }
            process_stream_batch(state, conn, entries).await?;
            if cfg.batch_window_ms > 0 {
                sleep(Duration::from_millis(cfg.batch_window_ms)).await;
            }
            Ok::<(), anyhow::Error>(())
        }
        .await;

        match step_result {
            Ok(()) => {
                consecutive_failures = 0;
                mark_stream_iteration_success(state).await;
            }
            Err(err) => {
                consecutive_failures = consecutive_failures.saturating_add(1);
                let backoff_ms = compute_retry_backoff_ms(cfg, consecutive_failures);
                let reason = err.to_string();
                record_stream_retry_attempt(state, consecutive_failures, backoff_ms, &reason).await;
                if consecutive_failures > cfg.max_retries_before_fallback {
                    return Err(err).context("order stream retry budget exhausted");
                }
                sleep(Duration::from_millis(backoff_ms)).await;
            }
        }
    }
}

fn should_run_stream_maintenance(cfg: &OrderEventsStreamConfig, last_at_ms: u64) -> bool {
    if cfg.reclaim_interval_ms == 0 {
        return false;
    }
    if last_at_ms == 0 {
        return true;
    }
    current_millis().saturating_sub(last_at_ms) >= cfg.reclaim_interval_ms
}

async fn run_stream_maintenance(
    state: &AppState,
    conn: &mut MultiplexedConnection,
) -> anyhow::Result<()> {
    refresh_stream_backlog_metrics(state, conn).await?;
    if !state.order_event_stream.reclaim_enabled {
        return Ok(());
    }
    reclaim_stuck_stream_entries(state, conn).await
}

fn compute_retry_backoff_ms(cfg: &OrderEventsStreamConfig, attempt: usize) -> u64 {
    let base = cfg.retry_backoff_base_ms.max(1);
    let max_backoff = cfg.retry_backoff_max_ms.max(base);
    let multiplier = 2u64.saturating_pow(attempt.saturating_sub(1) as u32);
    base.saturating_mul(multiplier).min(max_backoff)
}
