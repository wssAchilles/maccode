use std::time::Duration;

use anyhow::Context;
use futures_util::StreamExt;
use redis::{
    aio::{MultiplexedConnection, PubSub},
    streams::{StreamId, StreamReadOptions, StreamReadReply},
    AsyncCommands,
};
use tokio::time::sleep;
use tracing::{error, info, warn};

use crate::event_bus::publish_order_event;
use crate::gateway_types::{AppState, OrderEventsStreamConfig};

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
                warn!("redis stream ingest failed, fallback to pubsub mode: {err:#}");
                increment_stream_read_failure(&state, &err.to_string()).await;
            }
        }
    }

    run_order_events_pubsub_loop(&state).await
}

async fn run_order_events_stream_loop(state: &AppState) -> anyhow::Result<()> {
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
    loop {
        let cfg = &state.order_event_stream;
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
                record_stream_retry_attempt(state, consecutive_failures, backoff_ms, &err).await;
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
    let mut metrics = state.metrics.write().await;
    metrics.order_stream_events += stream_ids.len() as u64;
    metrics.last_order_stream_id = stream_ids.last().cloned();
    if acked < stream_ids.len() {
        metrics.order_stream_ack_failures += (stream_ids.len() - acked) as u64;
    }
    metrics.last_order_ingest_error = None;
    Ok(())
}

async fn increment_stream_read_failure(state: &AppState, reason: &str) {
    let mut metrics = state.metrics.write().await;
    metrics.order_stream_read_failures += 1;
    metrics.order_stream_fallbacks += 1;
    metrics.order_stream_consecutive_failures = 0;
    metrics.last_order_stream_retry_backoff_ms = None;
    metrics.last_order_ingest_error = Some(reason.to_string());
}

async fn clear_order_ingest_error(state: &AppState) {
    let mut metrics = state.metrics.write().await;
    metrics.last_order_ingest_error = None;
}

async fn run_order_events_pubsub_loop(state: &AppState) -> anyhow::Result<()> {
    let client = redis::Client::open(state.redis_url.as_str()).context("invalid redis url")?;
    let mut pubsub = client
        .get_async_pubsub()
        .await
        .context("redis pubsub connection failed")?;
    subscribe_order_channels(&mut pubsub, &state.redis_order_channels).await?;
    info!(
        "subscribed order channels (pubsub fallback): {}",
        state.redis_order_channels.join(",")
    );
    clear_order_ingest_error(state).await;

    let mut stream = pubsub.on_message();
    while let Some(message) = stream.next().await {
        let raw_payload: String = message.get_payload()?;
        let channel = message.get_channel_name().to_string();
        let payload = serde_json::from_str::<serde_json::Value>(&raw_payload)
            .unwrap_or_else(|_| serde_json::json!({ "raw": raw_payload }));
        publish_order_event(state, channel, payload).await;
    }

    Ok(())
}

async fn subscribe_order_channels(pubsub: &mut PubSub, channels: &[String]) -> anyhow::Result<()> {
    for channel in channels {
        pubsub.subscribe(channel).await?;
    }
    Ok(())
}

fn compute_retry_backoff_ms(cfg: &OrderEventsStreamConfig, attempt: usize) -> u64 {
    let base = cfg.retry_backoff_base_ms.max(1);
    let max_backoff = cfg.retry_backoff_max_ms.max(base);
    let multiplier = 2u64.saturating_pow(attempt.saturating_sub(1) as u32);
    base.saturating_mul(multiplier).min(max_backoff)
}

async fn record_stream_retry_attempt(
    state: &AppState,
    consecutive_failures: usize,
    backoff_ms: u64,
    err: &anyhow::Error,
) {
    let mut metrics = state.metrics.write().await;
    metrics.order_stream_retry_attempts += 1;
    metrics.order_stream_consecutive_failures = consecutive_failures as u64;
    metrics.last_order_stream_retry_backoff_ms = Some(backoff_ms);
    metrics.last_order_ingest_error = Some(err.to_string());
}

async fn mark_stream_iteration_success(state: &AppState) {
    let mut metrics = state.metrics.write().await;
    metrics.order_stream_consecutive_failures = 0;
    metrics.last_order_stream_retry_backoff_ms = None;
}
