use redis::{aio::MultiplexedConnection, AsyncCommands};
use tracing::warn;
use uuid::Uuid;

use crate::gateway_types::{AppState, MarketEvent};
use crate::gateway_utils::{current_millis, should_publish_legacy_channel};

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

    let symbol_channel = market_symbol_channel(state, event);

    if state.market_event_stream.enabled {
        match publish_market_event_stream(state, redis_conn, event, &symbol_channel).await {
            Ok(stream_id) => {
                let mut metrics = state.metrics.write().await;
                metrics.market_stream_events += 1;
                metrics.last_market_stream_id = Some(stream_id);
            }
            Err(()) => {
                increment_market_stream_publish_failure(state).await;
                if !state.market_event_stream.publish_legacy_pubsub {
                    return;
                }
            }
        }
    }

    if !state.market_event_stream.publish_legacy_pubsub {
        return;
    }

    let channels = market_pubsub_channels(state, &symbol_channel, &event.symbol);
    for channel in channels {
        if publish_redis_message(redis_conn, channel, payload)
            .await
            .is_err()
        {
            increment_redis_publish_failure(state).await;
            return;
        }
    }

    if let Some(tick_payload) = build_tick_payload(event) {
        let tick_channel = market_tick_channel(state, event);
        if publish_redis_message(redis_conn, tick_channel, tick_payload.as_str())
            .await
            .is_err()
        {
            increment_redis_publish_failure(state).await;
        }
    }
}

fn market_symbol_channel(state: &AppState, event: &MarketEvent) -> String {
    format!(
        "{}.{}",
        state.redis_orderbook_channel_prefix,
        event.symbol.as_str()
    )
}

fn market_tick_channel(state: &AppState, event: &MarketEvent) -> String {
    format!(
        "{}.{}",
        state.redis_tick_channel_prefix,
        event.symbol.as_str()
    )
}

fn market_pubsub_channels(
    state: &AppState,
    symbol_channel: &str,
    event_symbol: &str,
) -> Vec<String> {
    let publish_legacy_channel =
        should_publish_legacy_channel(&state.redis_orderbook_channel, event_symbol);
    if symbol_channel == state.redis_orderbook_channel || !publish_legacy_channel {
        return vec![symbol_channel.to_string()];
    }
    vec![
        symbol_channel.to_string(),
        state.redis_orderbook_channel.clone(),
    ]
}

fn build_tick_payload(event: &MarketEvent) -> Option<String> {
    let bid = event.bid_price.parse::<f64>().ok()?;
    let ask = event.ask_price.parse::<f64>().ok()?;
    Some(
        serde_json::json!({
            "symbol": event.symbol,
            "price": (bid + ask) / 2.0,
            "quantity": 0.0,
            "event_time": event.event_time.to_string()
        })
        .to_string(),
    )
}

async fn publish_market_event_stream(
    state: &AppState,
    redis_conn: &mut Option<MultiplexedConnection>,
    event: &MarketEvent,
    symbol_channel: &str,
) -> Result<String, ()> {
    let envelope = build_market_event_envelope(state, event, symbol_channel);
    let serialized = envelope.to_string();
    publish_stream_message(
        redis_conn,
        &state.market_event_stream.stream_key,
        serialized.as_str(),
        state.market_event_stream.max_len,
    )
    .await
}

fn build_market_event_envelope(
    state: &AppState,
    event: &MarketEvent,
    symbol_channel: &str,
) -> serde_json::Value {
    serde_json::json!({
        "event_type": "market.book_ticker.updated",
        "event_id": format!("evt-{}", Uuid::new_v4().simple()),
        "created_at": current_millis(),
        "schema_version": state.market_event_stream.schema_version,
        "channel": symbol_channel,
        "correlation_id": format!("{}:{}", event.symbol, event.event_time),
        "payload": event,
    })
}

async fn publish_stream_message(
    redis_conn: &mut Option<MultiplexedConnection>,
    stream_key: &str,
    payload: &str,
    max_len: usize,
) -> Result<String, ()> {
    let Some(conn) = redis_conn.as_mut() else {
        return Err(());
    };
    let mut command = redis::cmd("XADD");
    command
        .arg(stream_key)
        .arg("MAXLEN")
        .arg("~")
        .arg(max_len)
        .arg("*")
        .arg("data")
        .arg(payload);
    match command.query_async::<String>(conn).await {
        Ok(stream_id) => Ok(stream_id),
        Err(err) => {
            warn!("redis stream publish failed, disabling redis publish: {err}");
            *redis_conn = None;
            Err(())
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

async fn increment_market_stream_publish_failure(state: &AppState) {
    let mut metrics = state.metrics.write().await;
    metrics.market_stream_publish_failures += 1;
    metrics.market_redis_publish_failures += 1;
}
