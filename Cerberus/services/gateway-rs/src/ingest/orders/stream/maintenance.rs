use redis::aio::MultiplexedConnection;

use crate::gateway_types::{AppState, OrderEventsStreamConfig};
use crate::gateway_utils::current_millis;

use super::stream_reclaim::{reclaim_stuck_stream_entries, refresh_stream_backlog_metrics};

pub(super) fn should_run_stream_maintenance(
    cfg: &OrderEventsStreamConfig,
    last_at_ms: u64,
) -> bool {
    if cfg.reclaim_interval_ms == 0 {
        return false;
    }
    if last_at_ms == 0 {
        return true;
    }
    current_millis().saturating_sub(last_at_ms) >= cfg.reclaim_interval_ms
}

pub(super) async fn run_stream_maintenance(
    state: &AppState,
    conn: &mut MultiplexedConnection,
) -> anyhow::Result<()> {
    refresh_stream_backlog_metrics(state, conn).await?;
    if !state.order_event_stream.reclaim_enabled {
        return Ok(());
    }
    reclaim_stuck_stream_entries(state, conn).await
}
