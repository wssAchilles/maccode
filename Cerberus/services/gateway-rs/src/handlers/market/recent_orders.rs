use axum::{
    extract::{Extension, Query, State},
    Json,
};

use crate::event_bus::event_matches_account;
use crate::gateway_types::{AppState, RecentOrdersQuery, RequestContext};
use crate::handlers::common::with_request_context;

use super::filters::{payload_matches, payload_matches_ci};

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
