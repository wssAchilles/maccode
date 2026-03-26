use std::{
    collections::{HashMap, VecDeque},
    sync::Arc,
};

use reqwest::Client;
use tokio::sync::{broadcast, RwLock, Semaphore};

use crate::gateway_types::{MarketEvent, OrderEvent, TradingPolicy};

use super::{
    CachedAuthUser, CachedBinanceSymbolRule, CachedInternalServiceToken, CachedJsonPayload,
    ExchangeConfig, FirebaseAuthConfig, GatewayMetrics, InternalServiceAuthConfig, JwtAuthConfig,
    MarketEventsStreamPublishConfig, OrderEventsStreamConfig, StrategyUpstreamCircuitState,
    StrategyUpstreamConfig, SummaryInflightEntry,
};

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
    pub(crate) firebase_auth: FirebaseAuthConfig,
    pub(crate) auth_cache: Arc<RwLock<HashMap<String, CachedAuthUser>>>,
    pub(crate) strategy_base_url: Option<String>,
    pub(crate) started_at_unix: u64,
    pub(crate) order_event_stream: OrderEventsStreamConfig,
    pub(crate) strategy_summary_cache: Arc<RwLock<HashMap<String, CachedJsonPayload>>>,
    pub(crate) strategy_summary_cache_ttl_ms: u64,
    pub(crate) strategy_summary_batch_window_ms: u64,
    pub(crate) strategy_summary_inflight: Arc<RwLock<HashMap<String, SummaryInflightEntry>>>,
    pub(crate) ready_max_market_staleness_ms: u64,
    pub(crate) jwt_auth: JwtAuthConfig,
    pub(crate) unit_request_cost_usd: f64,
    pub(crate) market_event_stream: MarketEventsStreamPublishConfig,
    pub(crate) strategy_internal_auth: InternalServiceAuthConfig,
    pub(crate) strategy_internal_token_cache: Arc<RwLock<Option<CachedInternalServiceToken>>>,
    pub(crate) strategy_upstream: StrategyUpstreamConfig,
    pub(crate) strategy_upstream_circuit: Arc<RwLock<StrategyUpstreamCircuitState>>,
    pub(crate) strategy_upstream_semaphore: Arc<Semaphore>,
}

#[derive(Clone, Debug)]
pub(crate) struct RequestContext {
    pub(crate) request_id: String,
    pub(crate) idempotency_key: Option<String>,
}
