use axum::{
    extract::{Extension, Query, State},
    Json,
};

use crate::gateway_types::{AppState, RequestContext, SnapshotQuery};
use crate::handlers::common::with_request_context;

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
