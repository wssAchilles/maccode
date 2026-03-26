use axum::{
    extract::{Extension, Query, State},
    http::StatusCode,
    Json,
};

use crate::gateway_types::{AppState, KlineQuery, RequestContext};
use crate::handlers::common::{internal_err_json, with_request_context};

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
