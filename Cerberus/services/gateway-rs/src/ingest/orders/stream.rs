use std::time::Duration;

use anyhow::Context;
use redis::{
    aio::MultiplexedConnection,
    streams::{
        StreamAutoClaimOptions, StreamAutoClaimReply, StreamId, StreamInfoGroupsReply,
        StreamPendingCountReply, StreamPendingReply, StreamReadOptions, StreamReadReply,
    },
    AsyncCommands,
};
use tokio::time::sleep;
use tracing::{info, warn};

use super::stream_metrics::{
    add_reclaimed_events, clear_order_ingest_error, mark_ack_result, mark_poisoned_event,
    mark_reclaim_attempt, mark_stream_iteration_success, record_reclaim_failure,
    record_stream_retry_attempt, set_backlog_metrics,
};
use crate::event_bus::publish_order_event;
use crate::gateway_types::{AppState, OrderEventsStreamConfig};
use crate::gateway_utils::current_millis;

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

async fn ensure_stream_consumer_group(
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

async fn replay_pending_entries(
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
                warn!("order stream maintenance failed: {err:#}");
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
                warn!(
                    "order stream retrying after failure (attempt={}/{}, backoff_ms={}): {err:#}",
                    consecutive_failures, cfg.max_retries_before_fallback, backoff_ms
                );
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

async fn refresh_stream_backlog_metrics(
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

async fn reclaim_stuck_stream_entries(
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

async fn pending_delivery_count(
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

async fn read_stream_entries(
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

async fn process_stream_batch(
    state: &AppState,
    conn: &mut MultiplexedConnection,
    entries: Vec<StreamId>,
) -> anyhow::Result<()> {
    let mut stream_ids = Vec::with_capacity(entries.len());
    for entry in entries {
        let payload = decode_stream_payload(&entry).unwrap_or_else(|| {
            serde_json::json!({
                "raw": stringify_stream_entry(&entry),
            })
        });
        let channel = extract_stream_channel(&payload, &state.order_event_stream.stream_key);
        publish_order_event(state, channel, payload).await;
        stream_ids.push(entry.id);
    }
    ack_stream_entries(state, conn, &stream_ids).await?;
    Ok(())
}

fn decode_stream_payload(entry: &StreamId) -> Option<serde_json::Value> {
    let raw = entry
        .get::<String>("data")
        .or_else(|| entry.get::<String>("payload"))
        .or_else(|| entry.get::<String>("json"))?;
    serde_json::from_str::<serde_json::Value>(&raw).ok()
}

fn stringify_stream_entry(entry: &StreamId) -> String {
    let mut pairs = Vec::<String>::new();
    for (field, value) in &entry.map {
        let value_text = redis::from_redis_value::<String>(value).unwrap_or_default();
        pairs.push(format!("{field}={value_text}"));
    }
    pairs.join(",")
}

fn extract_stream_channel(payload: &serde_json::Value, fallback: &str) -> String {
    payload
        .get("channel")
        .or_else(|| payload.get("event_type"))
        .and_then(|value| value.as_str())
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .unwrap_or(fallback)
        .to_string()
}

async fn ack_stream_entries(
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

fn compute_retry_backoff_ms(cfg: &OrderEventsStreamConfig, attempt: usize) -> u64 {
    let base = cfg.retry_backoff_base_ms.max(1);
    let max_backoff = cfg.retry_backoff_max_ms.max(base);
    let multiplier = 2u64.saturating_pow(attempt.saturating_sub(1) as u32);
    base.saturating_mul(multiplier).min(max_backoff)
}
