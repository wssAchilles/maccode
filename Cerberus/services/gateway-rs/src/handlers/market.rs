use axum::{
    extract::{Extension, Query, State},
    http::StatusCode,
    Json,
};

use crate::event_bus::event_matches_account;
use crate::gateway_types::{
    AppState, KlineQuery, RecentOrdersQuery, RequestContext, SnapshotQuery,
};
use crate::handlers::common::{internal_err_json, with_request_context};

pub(crate) async fn get_snapshot(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
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
    Json(with_request_context(
        serde_json::json!({
            "symbol": symbol,
            "symbols_tracked": symbols_tracked,
            "data": snapshot,
        }),
        ctx.request_id.as_str(),
        ctx.idempotency_key.as_deref(),
    ))
}

pub(crate) async fn get_recent_order_events(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
    Query(query): Query<RecentOrdersQuery>,
) -> impl axum::response::IntoResponse {
    let limit = query.limit.unwrap_or(50).clamp(1, 500);
    let channel_filter = query.channel.as_deref().filter(|v| !v.is_empty());
    let account_filter = query.account_id.as_deref().filter(|v| !v.is_empty());
    let symbol_filter = query
        .symbol
        .as_deref()
        .map(str::trim)
        .filter(|v| !v.is_empty())
        .map(str::to_ascii_uppercase);
    let order_id_filter = query
        .order_id
        .as_deref()
        .map(str::trim)
        .filter(|v| !v.is_empty());
    let status_filter = query
        .status
        .as_deref()
        .map(str::trim)
        .filter(|v| !v.is_empty())
        .map(str::to_ascii_uppercase);
    let request_id_filter = query
        .request_id
        .as_deref()
        .map(str::trim)
        .filter(|v| !v.is_empty());

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
            .filter(|event| match symbol_filter.as_deref() {
                Some(symbol) => payload_matches_ci(&event.payload, &["symbol"], symbol),
                None => true,
            })
            .filter(|event| match order_id_filter {
                Some(order_id) => {
                    payload_matches(&event.payload, &["order_id", "orderId"], order_id)
                }
                None => true,
            })
            .filter(|event| match status_filter.as_deref() {
                Some(status) => payload_matches_ci(&event.payload, &["status"], status),
                None => true,
            })
            .filter(|event| match request_id_filter {
                Some(request_id) => {
                    payload_matches(&event.payload, &["request_id", "requestId"], request_id)
                }
                None => true,
            })
            .take(limit)
            .cloned()
            .collect::<Vec<_>>()
    };

    Json(with_request_context(
        serde_json::json!({
            "count": events.len(),
            "events": events,
        }),
        ctx.request_id.as_str(),
        ctx.idempotency_key.as_deref(),
    ))
}

fn payload_matches(payload: &serde_json::Value, keys: &[&str], expected: &str) -> bool {
    payload_text(payload, keys).is_some_and(|value| value == expected)
}

fn payload_matches_ci(payload: &serde_json::Value, keys: &[&str], expected: &str) -> bool {
    payload_text(payload, keys).is_some_and(|value| value.eq_ignore_ascii_case(expected))
}

fn payload_text(payload: &serde_json::Value, keys: &[&str]) -> Option<String> {
    if let Some(value) = payload_lookup(payload, keys) {
        return Some(value);
    }

    for nested in ["payload", "order", "execution", "error"] {
        if let Some(value) = payload
            .get(nested)
            .and_then(|child| payload_lookup(child, keys))
        {
            return Some(value);
        }
    }

    None
}

fn payload_lookup(payload: &serde_json::Value, keys: &[&str]) -> Option<String> {
    keys.iter()
        .find_map(|key| payload.get(*key).and_then(|value| value.as_str()))
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string)
}

#[cfg(test)]
mod tests {
    use super::{payload_matches, payload_matches_ci, payload_text};

    #[test]
    fn payload_text_reads_nested_execution_fields() {
        let payload = serde_json::json!({
            "execution": {
                "order_id": "ord-1",
                "symbol": "BTCUSDT"
            }
        });
        assert_eq!(
            payload_text(&payload, &["order_id"]).as_deref(),
            Some("ord-1")
        );
        assert_eq!(
            payload_text(&payload, &["symbol"]).as_deref(),
            Some("BTCUSDT")
        );
    }

    #[test]
    fn payload_matches_supports_case_insensitive_status() {
        let payload = serde_json::json!({
            "status": "submitted",
            "request_id": "rid-1"
        });
        assert!(payload_matches_ci(&payload, &["status"], "SUBMITTED"));
        assert!(payload_matches(&payload, &["request_id"], "rid-1"));
    }
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

    Ok(Json(with_request_context(
        serde_json::json!({
            "candles": resp,
        }),
        request_id,
        ctx.idempotency_key.as_deref(),
    )))
}
