use axum::{
    http::{
        header::{ACCEPT, AUTHORIZATION, CONTENT_TYPE, ORIGIN},
        HeaderName, HeaderValue,
    },
    middleware,
    routing::{get, post},
    Router,
};
use tower_http::cors::{Any, CorsLayer};

use crate::gateway_types::{
    AppState, IDEMPOTENCY_KEY_ALT_HEADER, IDEMPOTENCY_KEY_HEADER, REQUEST_ID_HEADER,
};
use crate::handlers::{
    market::{get_klines, get_recent_order_events, get_snapshot},
    system::{get_metrics, get_metrics_json, health, ready, request_context_middleware},
    trading::{
        activate_inference_model,
        binance_order_test, cancel_alpaca_order, create_alpaca_order, get_alpaca_account,
        get_binance_symbol_rules, get_external_status, get_inference_models,
        get_strategy_summary, get_trading_policy, promote_inference_rollout,
        rollback_inference_rollout,
    },
};
use crate::ws::{ws_market, ws_orders};

pub(crate) fn build_router(state: AppState, cors_allow_origins: &str) -> Router {
    let protected_api = Router::new()
        .route("/api/v1/orders/events/recent", get(get_recent_order_events))
        .route("/api/v1/strategy/summary", get(get_strategy_summary))
        .route("/api/v1/inference/models", get(get_inference_models))
        .route("/api/v1/inference/rollout/promote", post(promote_inference_rollout))
        .route("/api/v1/inference/rollout/rollback", post(rollback_inference_rollout))
        .route("/api/v1/inference/models/activate", post(activate_inference_model))
        .route("/api/v1/trading/policy", get(get_trading_policy))
        .route(
            "/api/v1/binance/symbol-rules",
            get(get_binance_symbol_rules),
        )
        .route("/api/v1/binance/order/test", post(binance_order_test))
        .route("/api/v1/alpaca/account", get(get_alpaca_account))
        .route("/api/v1/alpaca/orders", post(create_alpaca_order))
        .route(
            "/api/v1/alpaca/orders/{order_id}/cancel",
            post(cancel_alpaca_order),
        )
        .route_layer(middleware::from_fn_with_state(
            state.clone(),
            crate::handlers::system::require_gateway_jwt,
        ))
        .route_layer(middleware::from_fn_with_state(
            state.clone(),
            crate::handlers::system::require_firebase_auth,
        ));

    let rest_api = Router::new()
        .route("/health", get(health))
        .route("/ready", get(ready))
        .route("/metrics", get(get_metrics))
        .route("/api/v1/metrics", get(get_metrics_json))
        .route("/api/v1/klines", get(get_klines))
        .route("/api/v1/orderbook/snapshot", get(get_snapshot))
        .route("/api/v1/external/status", get(get_external_status))
        .merge(protected_api)
        .route_layer(middleware::from_fn_with_state(
            state.clone(),
            request_context_middleware,
        ));

    Router::new()
        .merge(rest_api)
        .route("/ws/market", get(ws_market))
        .route("/ws/orders", get(ws_orders))
        .layer(build_cors_layer(cors_allow_origins))
        .with_state(state)
}

fn build_cors_layer(raw_origins: &str) -> CorsLayer {
    let allow_headers = [
        AUTHORIZATION,
        CONTENT_TYPE,
        ACCEPT,
        ORIGIN,
        HeaderName::from_static(REQUEST_ID_HEADER),
        HeaderName::from_static(IDEMPOTENCY_KEY_HEADER),
        HeaderName::from_static(IDEMPOTENCY_KEY_ALT_HEADER),
    ];

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
