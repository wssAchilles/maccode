use anyhow::Context;
use redis::{aio::MultiplexedConnection, AsyncCommands};
use tracing::info;

use crate::gateway_types::{AppState, OrderEventsStreamConfig};

use super::stream_io::read_stream_entries;
use super::stream_processing::process_stream_batch;

pub(super) async fn ensure_stream_consumer_group(
    conn: &mut MultiplexedConnection,
    cfg: &OrderEventsStreamConfig,
) -> anyhow::Result<()> {
    let created: redis::RedisResult<()> = conn
        .xgroup_create_mkstream(&cfg.stream_key, &cfg.consumer_group, "0")
        .await;
    if let Err(err) = created {
        let message = err.to_string();
        if !message.contains("BUSYGROUP") {
            return Err(err).context("xgroup create failed");
        }
    }
    let _: redis::RedisResult<bool> = conn
        .xgroup_createconsumer(&cfg.stream_key, &cfg.consumer_group, &cfg.consumer_name)
        .await;
    Ok(())
}

pub(super) async fn replay_pending_entries(
    state: &AppState,
    conn: &mut MultiplexedConnection,
) -> anyhow::Result<()> {
    let cfg = &state.order_event_stream;
    let pending = read_stream_entries(conn, cfg, "0", cfg.pending_replay_count, 10).await?;
    if pending.is_empty() {
        return Ok(());
    }
    info!(
        "replaying {} pending stream entries for consumer {}",
        pending.len(),
        cfg.consumer_name
    );
    process_stream_batch(state, conn, pending).await
}
