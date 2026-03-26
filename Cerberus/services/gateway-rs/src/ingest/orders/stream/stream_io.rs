use anyhow::Context;
use redis::{
    aio::MultiplexedConnection,
    streams::{StreamId, StreamPendingCountReply, StreamReadOptions, StreamReadReply},
    AsyncCommands,
};

use crate::gateway_types::{AppState, OrderEventsStreamConfig};

use super::super::stream_metrics::mark_ack_result;

pub(super) async fn read_stream_entries(
    conn: &mut MultiplexedConnection,
    cfg: &OrderEventsStreamConfig,
    id: &str,
    count: usize,
    block_ms: usize,
) -> anyhow::Result<Vec<StreamId>> {
    let options = StreamReadOptions::default()
        .group(&cfg.consumer_group, &cfg.consumer_name)
        .count(count)
        .block(block_ms);
    let read: Option<StreamReadReply> = conn
        .xread_options(&[&cfg.stream_key], &[id], &options)
        .await
        .context("xreadgroup failed")?;
    let Some(reply) = read else {
        return Ok(Vec::new());
    };
    Ok(reply
        .keys
        .into_iter()
        .flat_map(|key| key.ids.into_iter())
        .collect::<Vec<_>>())
}

pub(super) async fn ack_stream_entries(
    state: &AppState,
    conn: &mut MultiplexedConnection,
    stream_ids: &[String],
) -> anyhow::Result<()> {
    if stream_ids.is_empty() {
        return Ok(());
    }

    let cfg = &state.order_event_stream;
    let ids = stream_ids.iter().map(String::as_str).collect::<Vec<_>>();
    let acked: usize = conn
        .xack(&cfg.stream_key, &cfg.consumer_group, &ids)
        .await
        .context("xack failed")?;
    mark_ack_result(state, stream_ids, acked).await;
    Ok(())
}

pub(super) async fn pending_delivery_count(
    state: &AppState,
    conn: &mut MultiplexedConnection,
    stream_id: &str,
) -> anyhow::Result<usize> {
    let cfg = &state.order_event_stream;
    let details: StreamPendingCountReply = conn
        .xpending_count(
            &cfg.stream_key,
            &cfg.consumer_group,
            stream_id,
            stream_id,
            1,
        )
        .await
        .context("xpending_count failed")?;
    Ok(details
        .ids
        .first()
        .map(|entry| entry.times_delivered)
        .unwrap_or(1))
}
