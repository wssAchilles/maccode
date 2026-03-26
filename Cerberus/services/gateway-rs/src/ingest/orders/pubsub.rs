use anyhow::Context;
use futures_util::StreamExt;
use redis::aio::PubSub;
use tracing::info;

use crate::event_bus::publish_order_event;
use crate::gateway_types::AppState;

pub(super) async fn run_order_events_pubsub_loop(state: &AppState) -> anyhow::Result<()> {
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

async fn clear_order_ingest_error(state: &AppState) {
    let mut metrics = state.metrics.write().await;
    metrics.last_order_ingest_error = None;
}
