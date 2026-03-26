use anyhow::Context;
use std::time::Duration;

use redis::aio::MultiplexedConnection;
use tokio::time::sleep;

use crate::gateway_types::{AppState, OrderEventsStreamConfig};
use crate::gateway_utils::current_millis;

use super::super::stream_metrics::{
    mark_stream_iteration_success, record_reclaim_failure, record_stream_retry_attempt,
};
use super::maintenance::{run_stream_maintenance, should_run_stream_maintenance};
use super::stream_io::read_stream_entries;
use super::stream_processing::process_stream_batch;

pub(super) async fn stream_consume_loop(
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

        match consume_stream_once(state, conn, cfg).await {
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

async fn consume_stream_once(
    state: &AppState,
    conn: &mut MultiplexedConnection,
    cfg: &OrderEventsStreamConfig,
) -> anyhow::Result<()> {
    let entries =
        read_stream_entries(conn, cfg, ">", cfg.read_batch_size, cfg.read_block_ms).await?;
    if entries.is_empty() {
        return Ok(());
    }
    process_stream_batch(state, conn, entries).await?;
    if cfg.batch_window_ms > 0 {
        sleep(Duration::from_millis(cfg.batch_window_ms)).await;
    }
    Ok(())
}

fn compute_retry_backoff_ms(cfg: &OrderEventsStreamConfig, attempt: usize) -> u64 {
    let base = cfg.retry_backoff_base_ms.max(1);
    let max_backoff = cfg.retry_backoff_max_ms.max(base);
    let multiplier = 2u64.saturating_pow(attempt.saturating_sub(1) as u32);
    base.saturating_mul(multiplier).min(max_backoff)
}
