use std::{
    collections::{HashMap, VecDeque},
    env,
    net::SocketAddr,
    sync::Arc,
};

use anyhow::Context;
use axum::{
    http::{
        header::{ACCEPT, AUTHORIZATION, CONTENT_TYPE, ORIGIN},
        HeaderValue,
    },
    middleware,
    routing::{get, post},
    Router,
};
use reqwest::Client;
use tokio::sync::{broadcast, RwLock};
use tower_http::cors::{Any, CorsLayer};
use tracing::{info, warn};

mod event_bus;
mod gateway_types;
mod gateway_utils;
mod handlers;
mod ingest;
mod ws;

use gateway_types::*;
use gateway_utils::{current_millis, env_flag, non_empty_env};
use handlers::{
    market::{get_klines, get_recent_order_events, get_snapshot},
    system::{get_metrics, get_metrics_json, health, ready, request_context_middleware},
    trading::{
        binance_order_test, cancel_alpaca_order, create_alpaca_order, get_alpaca_account,
        get_binance_symbol_rules, get_external_status, get_strategy_summary, get_trading_policy,
    },
};
use ingest::{spawn_market_ingest, spawn_order_events_ingest};
use ws::{ws_market, ws_orders};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    let port = env::var("PORT").unwrap_or_else(|_| "8080".to_string());
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
    let exchange = ExchangeConfig {
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
    };
    let trading_policy = TradingPolicy::from_env(&market_symbols);
    let strategy_base_url =
        non_empty_env("STRATEGY_BASE_URL").map(|raw| raw.trim_end_matches('/').to_string());
    let firebase_auth = FirebaseAuthConfig {
        required: env_flag("FIREBASE_AUTH_REQUIRED", false),
        project_id: non_empty_env("FIREBASE_PROJECT_ID"),
        web_api_key: non_empty_env("FIREBASE_WEB_API_KEY"),
    };
    if firebase_auth.required && firebase_auth.project_id.is_none() {
        warn!(
            "FIREBASE_AUTH_REQUIRED=true but FIREBASE_PROJECT_ID is empty; token audience checks rely on web API key only"
        );
    }
    let cors_allow_origins = env::var("CORS_ALLOW_ORIGINS").unwrap_or_else(|_| "*".to_string());

    let (market_tx, _) = broadcast::channel::<MarketEvent>(1024);
    let (orders_tx, _) = broadcast::channel::<OrderEvent>(1024);
    let state = AppState {
        http_client: Client::new(),
        kline_api_url: env::var("KLINE_API_URL").unwrap_or_else(|_| DEFAULT_KLINE_API.to_string()),
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
    };

    spawn_market_ingest(state.clone());
    spawn_order_events_ingest(state.clone());

    let protected_api = Router::new()
        .route("/api/v1/orders/events/recent", get(get_recent_order_events))
        .route("/api/v1/strategy/summary", get(get_strategy_summary))
        .route("/api/v1/trading/policy", get(get_trading_policy))
        .route("/api/v1/binance/symbol-rules", get(get_binance_symbol_rules))
        .route("/api/v1/binance/order/test", post(binance_order_test))
        .route("/api/v1/alpaca/account", get(get_alpaca_account))
        .route("/api/v1/alpaca/orders", post(create_alpaca_order))
        .route(
            "/api/v1/alpaca/orders/{order_id}/cancel",
            post(cancel_alpaca_order),
        )
        .route_layer(middleware::from_fn_with_state(
            state.clone(),
            handlers::system::require_firebase_auth,
        ));

    let cors_layer = build_cors_layer(&cors_allow_origins);

    let app = Router::new()
        .route("/health", get(health))
        .route("/ready", get(ready))
        .route("/metrics", get(get_metrics))
        .route("/api/v1/metrics", get(get_metrics_json))
        .route("/api/v1/klines", get(get_klines))
        .route("/api/v1/orderbook/snapshot", get(get_snapshot))
        .route("/api/v1/external/status", get(get_external_status))
        .route("/ws/market", get(ws_market))
        .route("/ws/orders", get(ws_orders))
        .merge(protected_api)
        .layer(cors_layer)
        .layer(middleware::from_fn(request_context_middleware))
        .with_state(state);

    let addr: SocketAddr = format!("0.0.0.0:{port}")
        .parse()
        .context("invalid bind address")?;

    info!("gateway listening on {addr}");

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

fn build_cors_layer(raw_origins: &str) -> CorsLayer {
    let allow_headers = [AUTHORIZATION, CONTENT_TYPE, ACCEPT, ORIGIN];
    let trimmed = raw_origins.trim();
    if trimmed == "*" || trimmed.is_empty() {
        return CorsLayer::new()
            .allow_origin(Any)
            .allow_headers(allow_headers)
            .allow_methods(Any);
    }

    let origins = trimmed
        .split(',')
        .map(str::trim)
        .filter(|origin| !origin.is_empty())
        .filter_map(|origin| HeaderValue::from_str(origin).ok())
        .collect::<Vec<_>>();

    if origins.is_empty() {
        return CorsLayer::new()
            .allow_origin(Any)
            .allow_headers(allow_headers)
            .allow_methods(Any);
    }

    CorsLayer::new()
        .allow_origin(origins)
        .allow_headers(allow_headers)
        .allow_methods(Any)
}
