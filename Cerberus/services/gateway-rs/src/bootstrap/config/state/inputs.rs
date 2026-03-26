use std::env;

use crate::gateway_types::{parse_market_symbols, DEFAULT_MARKET_SYMBOLS};
use crate::gateway_utils::non_empty_env;

#[derive(Clone, Debug)]
pub(super) struct StateInputs {
    pub(super) redis_url: String,
    pub(super) redis_orderbook_channel: String,
    pub(super) redis_orderbook_channel_prefix: String,
    pub(super) redis_tick_channel_prefix: String,
    pub(super) market_symbols: Vec<String>,
    pub(super) redis_order_channels: Vec<String>,
    pub(super) strategy_base_url: Option<String>,
}

pub(super) fn load_state_inputs() -> StateInputs {
    StateInputs {
        redis_url: env::var("REDIS_URL").unwrap_or_else(|_| "redis://localhost:6379/0".to_string()),
        redis_orderbook_channel: env::var("REDIS_ORDERBOOK_CHANNEL")
            .unwrap_or_else(|_| "md.orderbook.BTCUSDT".to_string()),
        redis_orderbook_channel_prefix: env::var("REDIS_ORDERBOOK_CHANNEL_PREFIX")
            .unwrap_or_else(|_| "md.orderbook".to_string()),
        redis_tick_channel_prefix: env::var("REDIS_TICK_CHANNEL_PREFIX")
            .unwrap_or_else(|_| "md.ticks".to_string()),
        market_symbols: parse_market_symbols(
            &env::var("MARKET_SYMBOLS").unwrap_or_else(|_| DEFAULT_MARKET_SYMBOLS.to_string()),
        ),
        redis_order_channels: env::var("REDIS_ORDER_EVENTS_CHANNELS")
            .unwrap_or_else(|_| "strategy.signals.default,trade.executions.default".to_string())
            .split(',')
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .map(ToOwned::to_owned)
            .collect::<Vec<_>>(),
        strategy_base_url: non_empty_env("STRATEGY_BASE_URL")
            .map(|raw| raw.trim_end_matches('/').to_string()),
    }
}
