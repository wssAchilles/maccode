use axum::{
    extract::{Extension, Query, State},
    http::StatusCode,
    Json,
};

use crate::event_bus::event_matches_account;
use crate::gateway_types::{
    AppState, KlineQuery, RecentOrdersQuery, RequestContext, SnapshotQuery,
};
use crate::handlers::common::internal_err_json;

pub(crate) async fn get_snapshot(
    State(state): State<AppState>,
    Query(query): Query<SnapshotQuery>,
) -> impl axum::response::IntoResponse {
    let symbol = query
        .symbol
        .map(|s| s.trim().to_ascii_uppercase())
        .filter(|s| !s.is_empty());

    let snapshot = if let Some(symbol) = symbol.as_ref() {
        state.latest_by_symbol.read().await.get(symbol).cloned()
    } else {
        state.latest_event.read().await.clone()
    };

    let symbols_tracked = state.latest_by_symbol.read().await.len();
    Json(serde_json::json!({
        "symbol": symbol,
        "symbols_tracked": symbols_tracked,
        "data": snapshot
    }))
}

pub(crate) async fn get_recent_order_events(
    State(state): State<AppState>,
    Query(query): Query<RecentOrdersQuery>,
) -> impl axum::response::IntoResponse {
    let limit = query.limit.unwrap_or(50).clamp(1, 500);
    let channel_filter = query.channel.as_deref().filter(|v| !v.is_empty());
    let account_filter = query.account_id.as_deref().filter(|v| !v.is_empty());

    let events = {
        let guard = state.recent_order_events.read().await;
        guard
            .iter()
            .rev()
            .filter(|event| match channel_filter {
                Some(channel) => event.channel == channel,
                None => true,
            })
            .filter(|event| match account_filter {
                Some(account_id) => event_matches_account(event, account_id),
                None => true,
            })
            .take(limit)
            .cloned()
            .collect::<Vec<_>>()
    };

    Json(serde_json::json!({
        "count": events.len(),
        "events": events
    }))
}

pub(crate) async fn get_klines(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
    Query(query): Query<KlineQuery>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let request_id = ctx.request_id.as_str();
    let symbol = query.symbol.unwrap_or_else(|| "BTCUSDT".to_string());
    let interval = query.interval.unwrap_or_else(|| "1m".to_string());
    let limit = query.limit.unwrap_or(100).to_string();

    let resp = state
        .http_client
        .get(state.kline_api_url.clone())
        .query(&[("symbol", symbol), ("interval", interval), ("limit", limit)])
        .send()
        .await
        .map_err(|err| internal_err_json(request_id, "upstream_request_failed", err))?
        .error_for_status()
        .map_err(|err| internal_err_json(request_id, "upstream_status_error", err))?
        .json::<serde_json::Value>()
        .await
        .map_err(|err| internal_err_json(request_id, "upstream_decode_failed", err))?;

    Ok(Json(serde_json::json!({ "candles": resp })))
}
