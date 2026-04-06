mod channels;
mod connection;
mod envelope;
mod metrics;

use redis::aio::MultiplexedConnection;

use crate::gateway_types::{AppState, MarketEvent};

use channels::{
    build_tick_payload, market_pubsub_channels, market_symbol_channel, market_tick_channel,
};
use connection::{publish_redis_message, publish_stream_message};
use envelope::build_market_event_envelope;
use metrics::{
    increment_market_stream_publish_failure, increment_redis_publish_failure,
    record_market_stream_success,
};

pub(super) use connection::connect_redis;

pub(super) async fn publish_market_event(
    state: &AppState,
    redis_conn: &mut Option<MultiplexedConnection>,
    event: &MarketEvent,
    payload: &str,
) -> bool {
    if redis_conn.is_none() {
        return false;
    }

    let symbol_channel = market_symbol_channel(state, event);
    let mut published = false;

    if state.market_event_stream.enabled {
        match publish_market_event_stream(state, redis_conn, event, &symbol_channel).await {
            Ok(stream_id) => {
                record_market_stream_success(state, stream_id).await;
                published = true;
                if !state.market_event_stream.publish_legacy_pubsub {
                    return true;
                }
            }
            Err(()) => {
                increment_market_stream_publish_failure(state).await;
                if !state.market_event_stream.publish_legacy_pubsub {
                    return false;
                }
            }
        }
    }

    if !state.market_event_stream.publish_legacy_pubsub {
        return false;
    }

    let channels = market_pubsub_channels(state, &symbol_channel, &event.symbol);
    for channel in channels {
        if publish_redis_message(redis_conn, channel, payload)
            .await
            .is_err()
        {
            increment_redis_publish_failure(state).await;
            return published;
        }
    }
    published = true;

    if let Some(tick_payload) = build_tick_payload(event) {
        let tick_channel = market_tick_channel(state, event);
        if publish_redis_message(redis_conn, tick_channel, tick_payload.as_str())
            .await
            .is_err()
        {
            increment_redis_publish_failure(state).await;
            return published;
        }
    }

    published
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
