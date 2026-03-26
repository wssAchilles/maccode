use crate::gateway_types::{AppState, MarketEvent};
use crate::gateway_utils::should_publish_legacy_channel;

pub(super) fn market_symbol_channel(state: &AppState, event: &MarketEvent) -> String {
    format!(
        "{}.{}",
        state.redis_orderbook_channel_prefix,
        event.symbol.as_str()
    )
}

pub(super) fn market_tick_channel(state: &AppState, event: &MarketEvent) -> String {
    format!(
        "{}.{}",
        state.redis_tick_channel_prefix,
        event.symbol.as_str()
    )
}

pub(super) fn market_pubsub_channels(
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

pub(super) fn build_tick_payload(event: &MarketEvent) -> Option<String> {
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
