mod aggregate;
mod cache;
mod downstream_errors;
mod fanout;
mod params;

use axum::{
    extract::{Extension, Query, State},
    http::StatusCode,
    Json,
};

use crate::gateway_types::{AppState, RequestContext, StrategySummaryQuery};
use crate::handlers::common::{error_body, with_request_context};
use aggregate::fetch_strategy_summary_aggregate;
use cache::{read_summary_cache, write_summary_cache};
use fanout::fetch_strategy_summary_fanout;
use params::parse_summary_request;

pub(crate) async fn get_strategy_summary(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
    Query(query): Query<StrategySummaryQuery>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let request_id = ctx.request_id.as_str();
    let strategy_base = state.strategy_base_url.as_ref().ok_or((
        StatusCode::SERVICE_UNAVAILABLE,
        error_body(
            "config_error",
            "STRATEGY_BASE_URL not configured",
            request_id,
        ),
    ))?;
    let summary_request = parse_summary_request(query, request_id)?;
    let cache_key = summary_request.cache_key();
    if let Some(cached) = read_summary_cache(&state, &cache_key).await {
        return Ok(Json(with_request_context(
            cached,
            request_id,
            ctx.idempotency_key.as_deref(),
        )));
    }

    let payload = if let Some(aggregated_payload) = fetch_strategy_summary_aggregate(
        &state,
        strategy_base,
        request_id,
        ctx.idempotency_key.as_deref(),
        &summary_request,
    )
    .await
    {
        aggregated_payload
    } else {
        fetch_strategy_summary_fanout(
            &state,
            strategy_base,
            request_id,
            ctx.idempotency_key.as_deref(),
            &summary_request,
        )
        .await
    };

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
