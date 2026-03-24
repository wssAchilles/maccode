use axum::{
    extract::{Extension, Query, State},
    http::StatusCode,
    Json,
};

use crate::gateway_types::{
    AppState, BinanceRuleQuery, CachedBinanceSymbolRule, RequestContext, BINANCE_RULE_TTL_MS,
};
use crate::gateway_utils::{
    binance_exchange_info_path, current_millis, parse_binance_symbol_rule, to_axum_status,
};
use crate::handlers::common::{error_body, internal_err_json};

pub(crate) async fn get_binance_symbol_rules(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
    Query(query): Query<BinanceRuleQuery>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let request_id = ctx.request_id.as_str();
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

    if let Some(cached) = {
        let guard = state.binance_rule_cache.read().await;
        guard.get(&symbol).cloned()
    } {
        let age = current_millis().saturating_sub(cached.cached_at);
        if age <= BINANCE_RULE_TTL_MS {
            return Ok(Json(serde_json::json!({
                "symbol": symbol,
                "cached": true,
                "cache_age_ms": age,
                "rule": cached.rule
            })));
        }
    }

    let exchange_info_path = binance_exchange_info_path(&state.exchange.binance_order_test_path);
    let url = format!(
        "{}{}",
        state.exchange.binance_api_base.trim_end_matches('/'),
        exchange_info_path
    );

    let resp = state
        .http_client
        .get(url)
        .query(&[("symbol", symbol.clone())])
        .send()
        .await
        .map_err(|err| internal_err_json(request_id, "upstream_request_failed", err))?;
    let status = resp.status();
    let body = resp
        .text()
        .await
        .map_err(|err| internal_err_json(request_id, "upstream_decode_failed", err))?;
    if !status.is_success() {
        return Err((
            to_axum_status(status),
            error_body("upstream_error", body, request_id),
        ));
    }

    let payload = serde_json::from_str::<serde_json::Value>(&body)
        .map_err(|err| internal_err_json(request_id, "upstream_decode_failed", err.to_string()))?;
    let rule = parse_binance_symbol_rule(&payload, &symbol);
    {
        let mut guard = state.binance_rule_cache.write().await;
        guard.insert(
            symbol.clone(),
            CachedBinanceSymbolRule {
                rule: rule.clone(),
                cached_at: current_millis(),
            },
        );
    }

    Ok(Json(serde_json::json!({
        "symbol": symbol,
        "cached": false,
        "cache_age_ms": 0,
        "rule": rule
    })))
}
