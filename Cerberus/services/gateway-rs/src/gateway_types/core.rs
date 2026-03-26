use std::{
    collections::{HashMap, VecDeque},
    sync::Arc,
};

use reqwest::Client;
use serde::Serialize;
use tokio::sync::{broadcast, RwLock, Semaphore};

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
    pub(crate) firebase_auth: FirebaseAuthConfig,
    pub(crate) auth_cache: Arc<RwLock<HashMap<String, CachedAuthUser>>>,
    pub(crate) strategy_base_url: Option<String>,
    pub(crate) started_at_unix: u64,
    pub(crate) order_event_stream: OrderEventsStreamConfig,
    pub(crate) strategy_summary_cache: Arc<RwLock<HashMap<String, CachedJsonPayload>>>,
    pub(crate) strategy_summary_cache_ttl_ms: u64,
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

#[derive(Clone, Default)]
pub(crate) struct FirebaseAuthConfig {
    pub(crate) required: bool,
    pub(crate) project_id: Option<String>,
    pub(crate) web_api_key: Option<String>,
}

#[derive(Clone, Default)]
pub(crate) struct JwtAuthConfig {
    pub(crate) enabled: bool,
    pub(crate) require_in_production: bool,
    pub(crate) environment: String,
    pub(crate) hs256_secret: Option<String>,
    pub(crate) issuer: Option<String>,
    pub(crate) audience: Option<String>,
}

impl JwtAuthConfig {
    pub(crate) fn effective_required(&self) -> bool {
        if self.enabled {
            return true;
        }
        self.require_in_production && self.environment.eq_ignore_ascii_case("production")
    }
}

#[derive(Clone)]
pub(crate) struct OrderEventsStreamConfig {
    pub(crate) enabled: bool,
    pub(crate) stream_key: String,
    pub(crate) consumer_group: String,
    pub(crate) consumer_name: String,
    pub(crate) read_batch_size: usize,
    pub(crate) read_block_ms: usize,
    pub(crate) pending_replay_count: usize,
    pub(crate) batch_window_ms: u64,
    pub(crate) max_retries_before_fallback: usize,
    pub(crate) retry_backoff_base_ms: u64,
    pub(crate) retry_backoff_max_ms: u64,
    pub(crate) reclaim_enabled: bool,
    pub(crate) reclaim_interval_ms: u64,
    pub(crate) reclaim_idle_ms: u64,
    pub(crate) reclaim_batch_size: usize,
    pub(crate) max_delivery_attempts: usize,
    pub(crate) poison_stream_key: String,
    pub(crate) poison_stream_maxlen: usize,
    pub(crate) pending_warn_threshold: usize,
    pub(crate) lag_warn_threshold: usize,
}

#[derive(Clone)]
pub(crate) struct MarketEventsStreamPublishConfig {
    pub(crate) enabled: bool,
    pub(crate) stream_key: String,
    pub(crate) max_len: usize,
    pub(crate) publish_legacy_pubsub: bool,
    pub(crate) schema_version: String,
}

#[derive(Clone)]
pub(crate) struct InternalServiceAuthConfig {
    pub(crate) enabled: bool,
    pub(crate) audience: Option<String>,
    pub(crate) metadata_identity_url: String,
    pub(crate) token_cache_ttl_seconds: u64,
}

#[derive(Clone, Debug)]
pub(crate) struct CachedInternalServiceToken {
    pub(crate) token: String,
    pub(crate) expires_at_ms: u64,
}

#[derive(Clone)]
pub(crate) struct StrategyUpstreamConfig {
    pub(crate) timeout_ms: u64,
    pub(crate) health_timeout_ms: u64,
    pub(crate) max_inflight: usize,
    pub(crate) queue_timeout_ms: u64,
    pub(crate) circuit_enabled: bool,
    pub(crate) circuit_failure_threshold: u64,
    pub(crate) circuit_open_ms: u64,
}

#[derive(Clone, Debug, Default)]
pub(crate) struct StrategyUpstreamCircuitState {
    pub(crate) consecutive_failures: u64,
    pub(crate) opened_at_ms: Option<u64>,
    pub(crate) last_failure_reason: Option<String>,
}

#[derive(Clone, Debug)]
pub(crate) struct CachedJsonPayload {
    pub(crate) payload: serde_json::Value,
    pub(crate) cached_at: u64,
}

#[derive(Clone, Debug)]
pub(crate) struct AuthenticatedUser {
    pub(crate) uid: String,
    pub(crate) email: Option<String>,
}

#[derive(Clone, Debug)]
pub(crate) struct CachedAuthUser {
    pub(crate) user: AuthenticatedUser,
    pub(crate) expires_at_ms: u64,
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
    pub(crate) market_stream_events: u64,
    pub(crate) market_stream_publish_failures: u64,
    pub(crate) last_market_stream_id: Option<String>,
    pub(crate) last_market_event_at: Option<u64>,
    pub(crate) last_order_event_at: Option<u64>,
    pub(crate) last_market_ingest_error: Option<String>,
    pub(crate) last_order_ingest_error: Option<String>,
    pub(crate) http_requests_total: u64,
    pub(crate) http_requests_4xx: u64,
    pub(crate) http_requests_5xx: u64,
    pub(crate) last_http_latency_ms: Option<u64>,
    pub(crate) http_latency_samples_ms: VecDeque<u64>,
    pub(crate) order_stream_events: u64,
    pub(crate) order_stream_ack_failures: u64,
    pub(crate) order_stream_read_failures: u64,
    pub(crate) order_stream_retry_attempts: u64,
    pub(crate) order_stream_fallbacks: u64,
    pub(crate) order_stream_consecutive_failures: u64,
    pub(crate) last_order_stream_retry_backoff_ms: Option<u64>,
    pub(crate) last_order_stream_id: Option<String>,
    pub(crate) order_stream_pending: u64,
    pub(crate) order_stream_lag: u64,
    pub(crate) order_stream_reclaim_attempts: u64,
    pub(crate) order_stream_reclaimed_events: u64,
    pub(crate) order_stream_reclaim_failures: u64,
    pub(crate) order_stream_poisoned_events: u64,
    pub(crate) last_order_stream_reclaim_at: Option<u64>,
    pub(crate) last_order_stream_poison_id: Option<String>,
    pub(crate) strategy_upstream_requests_total: u64,
    pub(crate) strategy_upstream_failures_total: u64,
    pub(crate) strategy_upstream_auth_failures_total: u64,
    pub(crate) strategy_upstream_circuit_rejections_total: u64,
    pub(crate) strategy_upstream_queue_rejections_total: u64,
    pub(crate) strategy_upstream_circuit_open: bool,
    pub(crate) strategy_upstream_circuit_opened_at: Option<u64>,
    pub(crate) strategy_upstream_last_error: Option<String>,
}

#[derive(Debug, Clone)]
pub(crate) struct CachedBinanceSymbolRule {
    pub(crate) rule: BinanceSymbolRule,
    pub(crate) cached_at: u64,
}
