mod inputs;

use std::{
    collections::{HashMap, VecDeque},
    env,
    sync::Arc,
};

use reqwest::Client;
use tokio::sync::{broadcast, RwLock};

use crate::gateway_types::{
    AppState, GatewayMetrics, MarketEvent, OrderEvent, StrategyUpstreamCircuitState,
};
use crate::gateway_utils::current_millis;

use super::loaders::{
    load_exchange_config, load_firebase_auth_config, load_jwt_auth_config,
    load_market_event_stream_config, load_order_event_stream_config,
    load_strategy_internal_auth_config, load_strategy_upstream_config, parse_env_f64,
    parse_env_u64,
};
use super::runtime::BootstrapRuntime;
use inputs::load_state_inputs;

pub(crate) fn build_state_from_env(runtime: &BootstrapRuntime) -> AppState {
    let inputs = load_state_inputs();
    let exchange = load_exchange_config();
    let strategy_internal_auth =
        load_strategy_internal_auth_config(inputs.strategy_base_url.as_ref());
    let strategy_upstream = load_strategy_upstream_config();
    let strategy_summary_cache_ttl_ms =
        parse_env_u64("STRATEGY_SUMMARY_CACHE_TTL_MS").unwrap_or(1_500);
    let strategy_summary_batch_window_ms =
        parse_env_u64("STRATEGY_SUMMARY_BATCH_WINDOW_MS").unwrap_or(120);
    let ready_max_market_staleness_ms = parse_env_u64("READY_MAX_MARKET_STALENESS_MS").unwrap_or(0);
    let unit_request_cost_usd = parse_env_f64("UNIT_REQUEST_COST_USD")
        .filter(|value| *value >= 0.0)
        .unwrap_or(0.0);
    let order_event_stream = load_order_event_stream_config();
    let market_event_stream = load_market_event_stream_config();
    let jwt_auth = load_jwt_auth_config(runtime.app_env.as_str());
    let firebase_auth = load_firebase_auth_config();

    let (market_tx, _) = broadcast::channel::<MarketEvent>(1024);
    let (orders_tx, _) = broadcast::channel::<OrderEvent>(1024);

    AppState {
        http_client: Client::new(),
        kline_api_url: env::var("KLINE_API_URL")
            .unwrap_or_else(|_| crate::gateway_types::DEFAULT_KLINE_API.to_string()),
        market_tx,
        orders_tx,
        latest_event: Arc::new(RwLock::new(None)),
        latest_by_symbol: Arc::new(RwLock::new(HashMap::new())),
        recent_order_events: Arc::new(RwLock::new(VecDeque::new())),
        redis_url: inputs.redis_url,
        redis_orderbook_channel: inputs.redis_orderbook_channel,
        redis_orderbook_channel_prefix: inputs.redis_orderbook_channel_prefix,
        redis_tick_channel_prefix: inputs.redis_tick_channel_prefix,
        market_symbols: inputs.market_symbols.clone(),
        redis_order_channels: inputs.redis_order_channels,
        binance_rule_cache: Arc::new(RwLock::new(HashMap::new())),
        trading_policy: crate::gateway_types::TradingPolicy::from_env(&inputs.market_symbols),
        metrics: Arc::new(RwLock::new(GatewayMetrics::default())),
        exchange,
        firebase_auth,
        auth_cache: Arc::new(RwLock::new(HashMap::new())),
        strategy_base_url: inputs.strategy_base_url,
        started_at_unix: current_millis() / 1_000,
        order_event_stream,
        strategy_summary_cache: Arc::new(RwLock::new(HashMap::new())),
        strategy_summary_cache_ttl_ms,
        strategy_summary_batch_window_ms,
        strategy_summary_inflight: Arc::new(RwLock::new(HashMap::new())),
        ready_max_market_staleness_ms,
        jwt_auth,
        unit_request_cost_usd,
        market_event_stream,
        strategy_internal_auth,
        strategy_internal_token_cache: Arc::new(RwLock::new(None)),
        strategy_upstream_semaphore: Arc::new(tokio::sync::Semaphore::new(
            strategy_upstream.max_inflight,
        )),
        strategy_upstream_circuit: Arc::new(RwLock::new(StrategyUpstreamCircuitState::default())),
        strategy_upstream,
    }
}
