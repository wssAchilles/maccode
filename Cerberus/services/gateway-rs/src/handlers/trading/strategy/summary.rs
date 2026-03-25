use std::time::Duration;

use axum::{
    extract::{Extension, Query, State},
    http::StatusCode,
    Json,
};

use crate::gateway_types::{AppState, RequestContext, StrategySummaryQuery, REQUEST_ID_HEADER};
use crate::gateway_utils::{current_millis, with_strategy_internal_auth};
use crate::handlers::common::{error_body, with_request_context};

pub(crate) async fn get_strategy_summary(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
    Query(query): Query<StrategySummaryQuery>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let request_id = ctx.request_id.as_str();
    let base = state.strategy_base_url.as_ref().ok_or((
        StatusCode::SERVICE_UNAVAILABLE,
        error_body(
            "config_error",
            "STRATEGY_BASE_URL not configured",
            request_id,
        ),
    ))?;

    let symbol = query
        .symbol
        .unwrap_or_else(|| "BTCUSDT".to_string())
        .trim()
        .to_ascii_uppercase();
    if symbol.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            error_body("validation_error", "symbol is required", request_id),
        ));
    }
    let recent_limit = query.recent_limit.unwrap_or(8).clamp(1, 200);
    let source = query
        .source
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .unwrap_or("auto");
    if source != "auto" && source != "supabase" && source != "firestore" {
        return Err((
            StatusCode::BAD_REQUEST,
            error_body(
                "validation_error",
                "source must be one of: auto|supabase|firestore",
                request_id,
            ),
        ));
    }
    let orderbook_depth = query.orderbook_depth.unwrap_or(10).clamp(1, 200);
    let cache_key = format!("{symbol}:{recent_limit}:{source}:{orderbook_depth}");
    if let Some(cached) = read_summary_cache(&state, &cache_key).await {
        return Ok(Json(with_request_context(
            cached,
            request_id,
            ctx.idempotency_key.as_deref(),
        )));
    }

    let signal_path = "/api/v1/signal".to_string();
    let recent_path = format!("/api/v1/signals/recent?limit={recent_limit}&source={source}");
    let persistence_path = "/api/v1/status/persistence".to_string();
    let orderbook_path =
        format!("/api/v1/matching/orderbook?symbol={symbol}&depth={orderbook_depth}");

    let (signal, recent, persistence, orderbook) = tokio::join!(
        fetch_strategy_json(
            &state,
            base,
            &signal_path,
            request_id,
            ctx.idempotency_key.as_deref()
        ),
        fetch_strategy_json(
            &state,
            base,
            &recent_path,
            request_id,
            ctx.idempotency_key.as_deref()
        ),
        fetch_strategy_json(
            &state,
            base,
            &persistence_path,
            request_id,
            ctx.idempotency_key.as_deref(),
        ),
        fetch_strategy_json(
            &state,
            base,
            &orderbook_path,
            request_id,
            ctx.idempotency_key.as_deref(),
        ),
    );

    let payload = serde_json::json!({
        "strategy_base_url": base,
        "symbol": symbol,
        "source": source,
        "recent_limit": recent_limit,
        "orderbook_depth": orderbook_depth,
        "signal": signal,
        "recent_signals": recent,
        "persistence": persistence,
        "matching_orderbook": orderbook,
    });
    write_summary_cache(&state, cache_key, payload.clone()).await;
    Ok(Json(with_request_context(
        payload,
        request_id,
        ctx.idempotency_key.as_deref(),
    )))
}

pub(crate) async fn get_trading_policy(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
) -> impl axum::response::IntoResponse {
    Json(with_request_context(
        serde_json::json!({
            "policy": state.trading_policy,
        }),
        ctx.request_id.as_str(),
        ctx.idempotency_key.as_deref(),
    ))
}

async fn fetch_strategy_json(
    state: &AppState,
    strategy_base: &str,
    path_and_query: &str,
    request_id: &str,
    idempotency_key: Option<&str>,
) -> serde_json::Value {
    let url = format!("{}{}", strategy_base.trim_end_matches('/'), path_and_query);
    let mut req = state
        .http_client
        .get(url.clone())
        .header(REQUEST_ID_HEADER, request_id);
    if let Some(key) = idempotency_key {
        req = req.header("idempotency-key", key);
    }
    let req = match with_strategy_internal_auth(state, req).await {
        Ok(req) => req,
        Err(err) => {
            return serde_json::json!({
                "ok": false,
                "status_code": StatusCode::BAD_GATEWAY.as_u16(),
                "url": url,
                "error": structured_error(
                    "upstream_auth_failed",
                    err.to_string(),
                    request_id
                )
            });
        }
    };
    match req.timeout(Duration::from_millis(1800)).send().await {
        Ok(resp) => {
            let status = resp.status();
            match resp.json::<serde_json::Value>().await {
                Ok(payload) => {
                    if status.is_success() {
                        serde_json::json!({
                            "ok": true,
                            "status_code": status.as_u16(),
                            "url": url,
                            "payload": payload
                        })
                    } else {
                        let error = normalize_downstream_error(&payload, status, request_id);
                        serde_json::json!({
                            "ok": false,
                            "status_code": status.as_u16(),
                            "url": url,
                            "payload": payload,
                            "error": error
                        })
                    }
                }
                Err(err) => serde_json::json!({
                    "ok": false,
                    "status_code": status.as_u16(),
                    "url": url,
                    "error": structured_error(
                        "upstream_decode_failed",
                        format!("decode failed: {err}"),
                        request_id
                    )
                }),
            }
        }
        Err(err) => serde_json::json!({
            "ok": false,
            "status_code": StatusCode::BAD_GATEWAY.as_u16(),
            "url": url,
            "error": structured_error(
                "upstream_request_failed",
                err.to_string(),
                request_id
            )
        }),
    }
}

async fn read_summary_cache(state: &AppState, cache_key: &str) -> Option<serde_json::Value> {
    let now = current_millis();
    let ttl = state.strategy_summary_cache_ttl_ms;
    let cache = state.strategy_summary_cache.read().await;
    cache.get(cache_key).and_then(|entry| {
        if now.saturating_sub(entry.cached_at) <= ttl {
            Some(entry.payload.clone())
        } else {
            None
        }
    })
}

async fn write_summary_cache(state: &AppState, cache_key: String, payload: serde_json::Value) {
    let mut cache = state.strategy_summary_cache.write().await;
    cache.insert(
        cache_key,
        crate::gateway_types::CachedJsonPayload {
            payload,
            cached_at: current_millis(),
        },
    );
    if cache.len() > 256 {
        let keys = cache.keys().take(64).cloned().collect::<Vec<_>>();
        for key in keys {
            cache.remove(&key);
        }
    }
}

fn structured_error(code: &str, message: impl Into<String>, request_id: &str) -> serde_json::Value {
    serde_json::json!({
        "code": code,
        "message": message.into(),
        "request_id": request_id
    })
}

fn normalize_downstream_error(
    payload: &serde_json::Value,
    status: StatusCode,
    fallback_request_id: &str,
) -> serde_json::Value {
    if let Some(error) = payload.get("error").and_then(|value| value.as_object()) {
        let code = error
            .get("code")
            .and_then(|value| value.as_str())
            .filter(|value| !value.is_empty())
            .unwrap_or_else(|| default_error_code(status));
        let message = error
            .get("message")
            .and_then(|value| value.as_str())
            .filter(|value| !value.is_empty())
            .unwrap_or_else(|| default_error_message(status));
        let request_id = error
            .get("request_id")
            .and_then(|value| value.as_str())
            .filter(|value| !value.is_empty())
            .or_else(|| {
                payload
                    .get("request_id")
                    .and_then(|value| value.as_str())
                    .filter(|value| !value.is_empty())
            })
            .unwrap_or(fallback_request_id);
        return structured_error(code, message.to_string(), request_id);
    }

    if let Some(message) = payload
        .get("detail")
        .and_then(|value| value.as_str())
        .filter(|value| !value.is_empty())
    {
        return structured_error(
            default_error_code(status),
            message.to_string(),
            fallback_request_id,
        );
    }

    structured_error(
        default_error_code(status),
        default_error_message(status).to_string(),
        fallback_request_id,
    )
}

fn default_error_code(status: StatusCode) -> &'static str {
    if status.is_server_error() {
        "upstream_internal_error"
    } else if status.is_client_error() {
        "upstream_request_error"
    } else {
        "upstream_error"
    }
}

fn default_error_message(status: StatusCode) -> &'static str {
    if status == StatusCode::REQUEST_TIMEOUT {
        "request timeout"
    } else {
        "request failed"
    }
}
