use redis::{aio::MultiplexedConnection, AsyncCommands};
use tracing::warn;

use crate::gateway_types::{AppState, MarketEvent};
use crate::gateway_utils::should_publish_legacy_channel;

pub(super) async fn connect_redis(redis_url: &str) -> Option<MultiplexedConnection> {
    if redis_url.trim().is_empty() {
        warn!("REDIS_URL empty, running without Redis publish");
        return None;
    }

    let client = match redis::Client::open(redis_url) {
        Ok(client) => client,
        Err(err) => {
            warn!("invalid redis url, continue without Redis: {err}");
            return None;
        }
    };

    match client.get_multiplexed_async_connection().await {
        Ok(conn) => Some(conn),
        Err(err) => {
            warn!("redis connection failed, continue without Redis: {err}");
            None
        }
    }
}

pub(super) async fn publish_market_event(
    state: &AppState,
    redis_conn: &mut Option<MultiplexedConnection>,
    event: &MarketEvent,
    payload: &str,
) {
    if redis_conn.is_none() {
        return;
    }

    let symbol_channel = format!(
        "{}.{}",
        state.redis_orderbook_channel_prefix,
        event.symbol.as_str()
    );
    let publish_legacy_channel =
        should_publish_legacy_channel(&state.redis_orderbook_channel, &event.symbol);
    let channels = if symbol_channel == state.redis_orderbook_channel || !publish_legacy_channel {
        vec![symbol_channel]
    } else {
        vec![symbol_channel, state.redis_orderbook_channel.clone()]
    };

    for channel in channels {
        if publish_redis_message(redis_conn, channel, payload).await.is_err() {
            increment_redis_publish_failure(state).await;
            return;
        }
    }

    if let (Ok(bid), Ok(ask)) = (event.bid_price.parse::<f64>(), event.ask_price.parse::<f64>()) {
        let tick_channel = format!("{}.{}", state.redis_tick_channel_prefix, event.symbol.as_str());
        let tick_payload = serde_json::json!({
            "symbol": event.symbol,
            "price": (bid + ask) / 2.0,
            "quantity": 0.0,
            "event_time": event.event_time.to_string()
        })
        .to_string();
        if publish_redis_message(redis_conn, tick_channel, &tick_payload)
            .await
            .is_err()
        {
            increment_redis_publish_failure(state).await;
        }
    }
}

async fn publish_redis_message(
    redis_conn: &mut Option<MultiplexedConnection>,
    channel: String,
    payload: &str,
) -> Result<(), ()> {
    let Some(conn) = redis_conn.as_mut() else {
        return Err(());
    };
    if let Err(err) = conn.publish::<_, _, usize>(channel, payload).await {
        warn!("redis publish failed, disabling redis publish: {err}");
        *redis_conn = None;
        return Err(());
    }
    Ok(())
}

async fn increment_redis_publish_failure(state: &AppState) {
    let mut metrics = state.metrics.write().await;
    metrics.market_redis_publish_failures += 1;
}
