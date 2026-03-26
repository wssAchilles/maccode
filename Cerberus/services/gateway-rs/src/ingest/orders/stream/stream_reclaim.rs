use anyhow::Context;
use redis::{
    aio::MultiplexedConnection,
    streams::{
        StreamAutoClaimOptions, StreamAutoClaimReply, StreamId, StreamInfoGroupsReply,
        StreamPendingReply,
    },
    AsyncCommands,
};
use tracing::info;

use crate::gateway_types::AppState;
use crate::gateway_utils::current_millis;

use super::super::stream_metrics::{
    add_reclaimed_events, mark_poisoned_event, mark_reclaim_attempt, set_backlog_metrics,
};
use super::stream_io::{ack_stream_entries, pending_delivery_count};
use super::stream_payload::{decode_stream_payload, stringify_stream_entry};
use super::stream_processing::process_stream_batch;

pub(super) async fn refresh_stream_backlog_metrics(
    state: &AppState,
    conn: &mut MultiplexedConnection,
) -> anyhow::Result<()> {
    let cfg = &state.order_event_stream;
    let pending: StreamPendingReply = conn
        .xpending(&cfg.stream_key, &cfg.consumer_group)
        .await
        .context("xpending failed")?;
    let pending_count = pending.count() as u64;

    let groups: StreamInfoGroupsReply = conn
        .xinfo_groups(&cfg.stream_key)
        .await
        .context("xinfo groups failed")?;
    let lag = groups
        .groups
        .iter()
        .find(|group| group.name == cfg.consumer_group)
        .and_then(|group| group.lag)
        .unwrap_or(0) as u64;

    set_backlog_metrics(state, pending_count, lag).await;
    Ok(())
}

pub(super) async fn reclaim_stuck_stream_entries(
    state: &AppState,
    conn: &mut MultiplexedConnection,
) -> anyhow::Result<()> {
    let cfg = &state.order_event_stream;
    mark_reclaim_attempt(state).await;

    let options = StreamAutoClaimOptions::default().count(cfg.reclaim_batch_size);
    let reclaimed: StreamAutoClaimReply = conn
        .xautoclaim_options(
            &cfg.stream_key,
            &cfg.consumer_group,
            &cfg.consumer_name,
            cfg.reclaim_idle_ms,
            "0-0",
            options,
        )
        .await
        .context("xautoclaim failed")?;

    if reclaimed.claimed.is_empty() {
        return Ok(());
    }

    add_reclaimed_events(state, reclaimed.claimed.len() as u64).await;
    info!(
        "reclaimed {} pending order stream entries",
        reclaimed.claimed.len()
    );

    let mut poison_ack_ids = Vec::<String>::new();
    let mut processable_entries = Vec::<StreamId>::new();
    for entry in reclaimed.claimed {
        let deliveries = pending_delivery_count(state, conn, entry.id.as_str()).await?;
        if cfg.max_delivery_attempts > 0 && deliveries > cfg.max_delivery_attempts {
            publish_poison_entry(state, conn, &entry, deliveries).await?;
            poison_ack_ids.push(entry.id.clone());
            mark_poisoned_event(state, entry.id.as_str()).await;
        } else {
            processable_entries.push(entry);
        }
    }

    if !processable_entries.is_empty() {
        process_stream_batch(state, conn, processable_entries).await?;
    }
    if !poison_ack_ids.is_empty() {
        ack_stream_entries(state, conn, &poison_ack_ids).await?;
    }
    Ok(())
}

async fn publish_poison_entry(
    state: &AppState,
    conn: &mut MultiplexedConnection,
    entry: &StreamId,
    deliveries: usize,
) -> anyhow::Result<()> {
    let cfg = &state.order_event_stream;
    let payload = decode_stream_payload(entry).unwrap_or_else(|| {
        serde_json::json!({
            "raw": stringify_stream_entry(entry),
        })
    });
    let poison_data = serde_json::json!({
        "stream": cfg.stream_key,
        "group": cfg.consumer_group,
        "consumer": cfg.consumer_name,
        "stream_id": entry.id,
        "deliveries": deliveries,
        "reason": "max_delivery_attempts_exceeded",
        "created_at_ms": current_millis(),
        "schema_version": "v1",
        "payload": payload,
    });
    let body = serde_json::to_string(&poison_data).context("poison encode failed")?;
    let _: String = conn
        .xadd_maxlen(
            &cfg.poison_stream_key,
            redis::streams::StreamMaxlen::Approx(cfg.poison_stream_maxlen),
            "*",
            &[("data", body.as_str())],
        )
        .await
        .context("poison xadd failed")?;
    Ok(())
}
