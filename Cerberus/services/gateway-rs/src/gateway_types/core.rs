use std::{
    collections::{HashMap, VecDeque},
    sync::Arc,
};

use reqwest::Client;
use serde::Serialize;
use tokio::sync::{broadcast, RwLock};

use crate::gateway_types::{BinanceSymbolRule, MarketEvent, OrderEvent, TradingPolicy};

#[derive(Clone)]
pub(crate) struct AppState {
    pub(crate) http_client: Client,
    pub(crate) kline_api_url: String,
    pub(crate) market_tx: broadcast::Sender<MarketEvent>,
    pub(crate) orders_tx: broadcast::Sender<OrderEvent>,
    pub(crate) latest_event: Arc<RwLock<Option<MarketEvent>>>,
    pub(crate) latest_by_symbol: Arc<RwLock<HashMap<String, MarketEvent>>>,
    pub(crate) recent_order_events: Arc<RwLock<VecDeque<OrderEvent>>>,
    pub(crate) redis_url: String,
    pub(crate) redis_orderbook_channel: String,
    pub(crate) redis_orderbook_channel_prefix: String,
    pub(crate) redis_tick_channel_prefix: String,
    pub(crate) market_symbols: Vec<String>,
    pub(crate) redis_order_channels: Vec<String>,
    pub(crate) binance_rule_cache: Arc<RwLock<HashMap<String, CachedBinanceSymbolRule>>>,
    pub(crate) trading_policy: TradingPolicy,
    pub(crate) metrics: Arc<RwLock<GatewayMetrics>>,
    pub(crate) exchange: ExchangeConfig,
    pub(crate) strategy_base_url: Option<String>,
    pub(crate) started_at_unix: u64,
}

#[derive(Clone, Debug)]
pub(crate) struct RequestContext {
    pub(crate) request_id: String,
}

#[derive(Clone, Default)]
pub(crate) struct ExchangeConfig {
    pub(crate) binance_api_base: String,
    pub(crate) binance_order_test_path: String,
    pub(crate) binance_api_key: Option<String>,
    pub(crate) binance_api_secret: Option<String>,
    pub(crate) alpaca_trading_base: String,
    pub(crate) alpaca_api_key: Option<String>,
    pub(crate) alpaca_api_secret: Option<String>,
}

#[derive(Debug, Default, Clone, Serialize)]
pub(crate) struct GatewayMetrics {
    pub(crate) market_events: u64,
    pub(crate) order_events: u64,
    pub(crate) market_redis_publish_failures: u64,
    pub(crate) last_market_event_at: Option<u64>,
    pub(crate) last_order_event_at: Option<u64>,
    pub(crate) last_market_ingest_error: Option<String>,
    pub(crate) last_order_ingest_error: Option<String>,
}

#[derive(Debug, Clone)]
pub(crate) struct CachedBinanceSymbolRule {
    pub(crate) rule: BinanceSymbolRule,
    pub(crate) cached_at: u64,
}
