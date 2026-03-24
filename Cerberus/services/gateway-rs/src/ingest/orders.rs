use std::time::Duration;

use anyhow::Context;
use futures_util::StreamExt;
use tokio::time::sleep;
use tracing::{error, info, warn};

use crate::event_bus::publish_order_event;
use crate::gateway_types::AppState;

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

    let client = redis::Client::open(state.redis_url.as_str()).context("invalid redis url")?;
    let mut pubsub = client
        .get_async_pubsub()
        .await
        .context("redis pubsub connection failed")?;

    for channel in &state.redis_order_channels {
        pubsub.subscribe(channel).await?;
    }
    info!(
        "subscribed order channels: {}",
        state.redis_order_channels.join(",")
    );
    {
        let mut metrics = state.metrics.write().await;
        metrics.last_order_ingest_error = None;
    }

    let mut stream = pubsub.on_message();
    while let Some(message) = stream.next().await {
        let raw_payload: String = message.get_payload()?;
        let channel = message.get_channel_name().to_string();
        let payload = serde_json::from_str::<serde_json::Value>(&raw_payload)
            .unwrap_or_else(|_| serde_json::json!({ "raw": raw_payload }));

        publish_order_event(&state, channel, payload).await;
    }

    Ok(())
}
