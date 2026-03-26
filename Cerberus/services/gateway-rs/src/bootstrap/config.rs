use std::{
    collections::{HashMap, VecDeque},
    env,
    sync::Arc,
};

use anyhow::bail;
use reqwest::Client;
use tokio::sync::{broadcast, RwLock};
use tracing::warn;
use uuid::Uuid;

use crate::gateway_types::{
    parse_market_symbols, AppState, FirebaseAuthConfig, GatewayMetrics, InternalServiceAuthConfig,
    JwtAuthConfig, MarketEvent, MarketEventsStreamPublishConfig, OrderEvent,
    OrderEventsStreamConfig, StrategyUpstreamCircuitState, StrategyUpstreamConfig, TradingPolicy,
    DEFAULT_ALPACA_TRADING_BASE, DEFAULT_BINANCE_API_BASE, DEFAULT_BINANCE_ORDER_TEST_PATH,
    DEFAULT_MARKET_SYMBOLS,
};
use crate::gateway_utils::{current_millis, env_flag, non_empty_env};

#[derive(Debug, Clone)]
pub(crate) struct BootstrapRuntime {
    pub(crate) port: String,
    pub(crate) cors_allow_origins: String,
    pub(crate) app_env: String,
}

pub(crate) fn load_bootstrap_runtime() -> BootstrapRuntime {
    BootstrapRuntime {
        port: env::var("PORT").unwrap_or_else(|_| "8080".to_string()),
        cors_allow_origins: env::var("CORS_ALLOW_ORIGINS").unwrap_or_else(|_| "*".to_string()),
        app_env: env::var("APP_ENV").unwrap_or_else(|_| "development".to_string()),
    }
}

pub(crate) fn build_state_from_env(runtime: &BootstrapRuntime) -> AppState {
    let redis_url =
        env::var("REDIS_URL").unwrap_or_else(|_| "redis://localhost:6379/0".to_string());
    let redis_orderbook_channel =
        env::var("REDIS_ORDERBOOK_CHANNEL").unwrap_or_else(|_| "md.orderbook.BTCUSDT".to_string());
    let redis_orderbook_channel_prefix =
        env::var("REDIS_ORDERBOOK_CHANNEL_PREFIX").unwrap_or_else(|_| "md.orderbook".to_string());
    let redis_tick_channel_prefix =
        env::var("REDIS_TICK_CHANNEL_PREFIX").unwrap_or_else(|_| "md.ticks".to_string());

    let market_symbols = parse_market_symbols(
        &env::var("MARKET_SYMBOLS").unwrap_or_else(|_| DEFAULT_MARKET_SYMBOLS.to_string()),
    );
    let redis_order_channels = env::var("REDIS_ORDER_EVENTS_CHANNELS")
        .unwrap_or_else(|_| "strategy.signals.default,trade.executions.default".to_string())
        .split(',')
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(ToOwned::to_owned)
        .collect::<Vec<_>>();

    let exchange = load_exchange_config();
    let trading_policy = TradingPolicy::from_env(&market_symbols);
    let strategy_base_url =
        non_empty_env("STRATEGY_BASE_URL").map(|raw| raw.trim_end_matches('/').to_string());
    let strategy_internal_auth = load_strategy_internal_auth_config(strategy_base_url.as_ref());
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
        redis_url,
        redis_orderbook_channel,
        redis_orderbook_channel_prefix,
        redis_tick_channel_prefix,
        market_symbols,
        redis_order_channels,
        binance_rule_cache: Arc::new(RwLock::new(HashMap::new())),
        trading_policy,
        metrics: Arc::new(RwLock::new(GatewayMetrics::default())),
        exchange,
        firebase_auth,
        auth_cache: Arc::new(RwLock::new(HashMap::new())),
        strategy_base_url,
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

pub(crate) fn validate_runtime_policies(state: &AppState) -> anyhow::Result<()> {
    let is_production = state
        .jwt_auth
        .environment
        .eq_ignore_ascii_case("production");

    if state.strategy_internal_auth.enabled && state.strategy_internal_auth.audience.is_none() {
        let msg = "STRATEGY_INTERNAL_AUTH_ENABLED=true but STRATEGY_INTERNAL_AUTH_AUDIENCE/STRATEGY_BASE_URL is missing";
        if is_production {
            bail!("{msg}");
        }
        warn!("{msg}; upstream strategy calls will fail");
    }

    if state.jwt_auth.effective_required() && state.jwt_auth.hs256_secret.is_none() {
        let msg = "JWT auth is enabled/required but JWT_HS256_SECRET is missing";
        if is_production {
            bail!("{msg}");
        }
        warn!("{msg}; protected routes will reject requests");
    }

    if state.firebase_auth.required && state.firebase_auth.web_api_key.is_none() {
        bail!("FIREBASE_AUTH_REQUIRED=true but FIREBASE_WEB_API_KEY is missing");
    }

    if state.firebase_auth.required && state.firebase_auth.project_id.is_none() {
        warn!(
            "FIREBASE_AUTH_REQUIRED=true but FIREBASE_PROJECT_ID is empty; token audience checks rely on web API key only"
        );
    }

    if is_production && state.redis_url.trim().is_empty() {
        bail!("REDIS_URL cannot be empty in production");
    }
    if is_production
        && state.order_event_stream.enabled
        && state.order_event_stream.legacy_pubsub_fallback
    {
        bail!("REDIS_ORDER_EVENTS_LEGACY_PUBSUB_FALLBACK must be false when APP_ENV=production");
    }

    Ok(())
}

fn load_exchange_config() -> crate::gateway_types::ExchangeConfig {
    crate::gateway_types::ExchangeConfig {
        binance_api_base: env::var("BINANCE_API_BASE")
            .unwrap_or_else(|_| DEFAULT_BINANCE_API_BASE.to_string()),
        binance_order_test_path: env::var("BINANCE_ORDER_TEST_PATH")
            .unwrap_or_else(|_| DEFAULT_BINANCE_ORDER_TEST_PATH.to_string()),
        binance_api_key: non_empty_env("BINANCE_API_KEY"),
        binance_api_secret: non_empty_env("BINANCE_API_SECRET"),
        alpaca_trading_base: env::var("ALPACA_TRADING_BASE_URL")
            .unwrap_or_else(|_| DEFAULT_ALPACA_TRADING_BASE.to_string()),
        alpaca_api_key: non_empty_env("ALPACA_API_KEY"),
        alpaca_api_secret: non_empty_env("ALPACA_API_SECRET"),
    }
}

fn load_strategy_internal_auth_config(
    strategy_base_url: Option<&String>,
) -> InternalServiceAuthConfig {
    InternalServiceAuthConfig {
        enabled: env_flag("STRATEGY_INTERNAL_AUTH_ENABLED", false),
        audience: non_empty_env("STRATEGY_INTERNAL_AUTH_AUDIENCE")
            .or_else(|| strategy_base_url.cloned()),
        metadata_identity_url: env::var("GCP_METADATA_IDENTITY_URL").unwrap_or_else(|_| {
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity".to_string()
        }),
        token_cache_ttl_seconds: parse_env_u64("STRATEGY_INTERNAL_AUTH_TOKEN_TTL_SECONDS")
            .filter(|value| *value > 0)
            .unwrap_or(300),
    }
}

fn load_strategy_upstream_config() -> StrategyUpstreamConfig {
    StrategyUpstreamConfig {
        timeout_ms: parse_env_u64("STRATEGY_UPSTREAM_TIMEOUT_MS")
            .filter(|value| *value > 0)
            .unwrap_or(1_800),
        health_timeout_ms: parse_env_u64("STRATEGY_UPSTREAM_HEALTH_TIMEOUT_MS")
            .filter(|value| *value > 0)
            .unwrap_or(1_500),
        max_inflight: parse_env_usize("STRATEGY_UPSTREAM_MAX_INFLIGHT")
            .filter(|value| *value > 0)
            .unwrap_or(64),
        queue_timeout_ms: parse_env_u64("STRATEGY_UPSTREAM_QUEUE_TIMEOUT_MS")
            .filter(|value| *value > 0)
            .unwrap_or(250),
        circuit_enabled: env_flag("STRATEGY_UPSTREAM_CIRCUIT_ENABLED", true),
        circuit_failure_threshold: parse_env_u64("STRATEGY_UPSTREAM_CIRCUIT_FAILURE_THRESHOLD")
            .filter(|value| *value > 0)
            .unwrap_or(6),
        circuit_open_ms: parse_env_u64("STRATEGY_UPSTREAM_CIRCUIT_OPEN_MS")
            .filter(|value| *value > 0)
            .unwrap_or(15_000),
    }
}

fn load_order_event_stream_config() -> OrderEventsStreamConfig {
    OrderEventsStreamConfig {
        enabled: env_flag("REDIS_ORDER_EVENTS_STREAM_ENABLED", true),
        legacy_pubsub_fallback: env_flag("REDIS_ORDER_EVENTS_LEGACY_PUBSUB_FALLBACK", true),
        stream_key: env::var("REDIS_ORDER_EVENTS_STREAM_KEY")
            .unwrap_or_else(|_| "cerberus.order.events".to_string()),
        consumer_group: env::var("REDIS_ORDER_EVENTS_CONSUMER_GROUP")
            .unwrap_or_else(|_| "gateway-orders".to_string()),
        consumer_name: env::var("REDIS_ORDER_EVENTS_CONSUMER_NAME")
            .ok()
            .map(|raw| raw.trim().to_string())
            .filter(|raw| !raw.is_empty())
            .unwrap_or_else(|| format!("gateway-{}", Uuid::new_v4())),
        read_batch_size: parse_env_usize("REDIS_ORDER_EVENTS_READ_BATCH_SIZE")
            .filter(|value| *value > 0)
            .unwrap_or(64),
        read_block_ms: parse_env_usize("REDIS_ORDER_EVENTS_READ_BLOCK_MS")
            .filter(|value| *value > 0)
            .unwrap_or(3_000),
        pending_replay_count: parse_env_usize("REDIS_ORDER_EVENTS_PENDING_REPLAY_COUNT")
            .filter(|value| *value > 0)
            .unwrap_or(128),
        batch_window_ms: parse_env_u64("REDIS_ORDER_EVENTS_BATCH_WINDOW_MS").unwrap_or(100),
        max_retries_before_fallback: parse_env_usize(
            "REDIS_ORDER_EVENTS_MAX_RETRIES_BEFORE_FALLBACK",
        )
        .unwrap_or(6),
        retry_backoff_base_ms: parse_env_u64("REDIS_ORDER_EVENTS_RETRY_BACKOFF_MS")
            .filter(|value| *value > 0)
            .unwrap_or(200),
        retry_backoff_max_ms: parse_env_u64("REDIS_ORDER_EVENTS_RETRY_BACKOFF_MAX_MS")
            .filter(|value| *value > 0)
            .unwrap_or(5_000),
        reclaim_enabled: env_flag("REDIS_ORDER_EVENTS_RECLAIM_ENABLED", true),
        reclaim_interval_ms: parse_env_u64("REDIS_ORDER_EVENTS_RECLAIM_INTERVAL_MS")
            .unwrap_or(5_000),
        reclaim_idle_ms: parse_env_u64("REDIS_ORDER_EVENTS_RECLAIM_IDLE_MS")
            .filter(|value| *value > 0)
            .unwrap_or(30_000),
        reclaim_batch_size: parse_env_usize("REDIS_ORDER_EVENTS_RECLAIM_BATCH_SIZE")
            .filter(|value| *value > 0)
            .unwrap_or(64),
        max_delivery_attempts: parse_env_usize("REDIS_ORDER_EVENTS_MAX_DELIVERY_ATTEMPTS")
            .unwrap_or(8),
        poison_stream_key: env::var("REDIS_ORDER_EVENTS_POISON_STREAM_KEY")
            .ok()
            .map(|raw| raw.trim().to_string())
            .filter(|raw| !raw.is_empty())
            .unwrap_or_else(|| "cerberus.order.events.poison".to_string()),
        poison_stream_maxlen: parse_env_usize("REDIS_ORDER_EVENTS_POISON_STREAM_MAXLEN")
            .filter(|value| *value > 0)
            .unwrap_or(20_000),
        pending_warn_threshold: parse_env_usize("REDIS_ORDER_EVENTS_PENDING_WARN_THRESHOLD")
            .unwrap_or(2_000),
        lag_warn_threshold: parse_env_usize("REDIS_ORDER_EVENTS_LAG_WARN_THRESHOLD")
            .unwrap_or(2_000),
    }
}

fn load_market_event_stream_config() -> MarketEventsStreamPublishConfig {
    MarketEventsStreamPublishConfig {
        enabled: env_flag("REDIS_MARKET_EVENTS_STREAM_ENABLED", true),
        stream_key: env::var("REDIS_MARKET_EVENTS_STREAM_KEY")
            .unwrap_or_else(|_| "cerberus.market.events".to_string()),
        max_len: parse_env_usize("REDIS_MARKET_EVENTS_STREAM_MAXLEN")
            .filter(|value| *value > 0)
            .unwrap_or(50_000),
        publish_legacy_pubsub: env_flag("REDIS_MARKET_EVENTS_PUBLISH_LEGACY_PUBSUB", true),
        schema_version: env::var("CERBERUS_EVENT_SCHEMA_VERSION")
            .ok()
            .map(|raw| raw.trim().to_string())
            .filter(|raw| !raw.is_empty())
            .unwrap_or_else(|| "v1".to_string()),
    }
}

fn load_jwt_auth_config(app_env: &str) -> JwtAuthConfig {
    JwtAuthConfig {
        enabled: env_flag("JWT_AUTH_ENABLED", false),
        require_in_production: env_flag("JWT_AUTH_REQUIRE_IN_PRODUCTION", true),
        environment: app_env.to_string(),
        hs256_secret: non_empty_env("JWT_HS256_SECRET"),
        issuer: non_empty_env("JWT_ISSUER"),
        audience: non_empty_env("JWT_AUDIENCE"),
    }
}

fn load_firebase_auth_config() -> FirebaseAuthConfig {
    FirebaseAuthConfig {
        required: env_flag("FIREBASE_AUTH_REQUIRED", false),
        project_id: non_empty_env("FIREBASE_PROJECT_ID"),
        web_api_key: non_empty_env("FIREBASE_WEB_API_KEY"),
    }
}

fn parse_env_u64(key: &str) -> Option<u64> {
    env::var(key).ok()?.trim().parse::<u64>().ok()
}

fn parse_env_usize(key: &str) -> Option<usize> {
    env::var(key).ok()?.trim().parse::<usize>().ok()
}

fn parse_env_f64(key: &str) -> Option<f64> {
    env::var(key).ok()?.trim().parse::<f64>().ok()
}
