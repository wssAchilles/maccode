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
use tokio::time::{sleep, Duration};

use crate::gateway_types::{AppState, RequestContext, StrategySummaryQuery};
use crate::handlers::common::{error_body, with_request_context};
use aggregate::fetch_strategy_summary_aggregate;
use cache::{
    begin_summary_inflight, finish_summary_inflight, read_summary_cache, wait_for_summary_inflight,
    write_summary_cache, SummaryInflightRole,
};
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
        record_summary_cache_hit(&state).await;
        return Ok(Json(with_request_context(
            cached,
            request_id,
            ctx.idempotency_key.as_deref(),
        )));
    }

    match begin_summary_inflight(&state, &cache_key).await {
        SummaryInflightRole::Leader(waiter) => {
            if state.strategy_summary_batch_window_ms > 0 {
                sleep(Duration::from_millis(
                    state.strategy_summary_batch_window_ms,
                ))
                .await;
            }
            record_summary_cache_miss(&state).await;
            let payload = fetch_summary_payload(
                &state,
                strategy_base,
                request_id,
                ctx.idempotency_key.as_deref(),
                &summary_request,
            )
            .await;
            write_summary_cache(&state, cache_key.clone(), payload.clone()).await;
            finish_summary_inflight(&state, &cache_key, &waiter).await;
            Ok(Json(with_request_context(
                payload,
                request_id,
                ctx.idempotency_key.as_deref(),
            )))
        }
        SummaryInflightRole::Follower(waiter) => {
            record_summary_coalesced_wait(&state).await;
            wait_for_summary_inflight(&state, waiter).await;
            if let Some(cached) = read_summary_cache(&state, &cache_key).await {
                record_summary_cache_hit(&state).await;
                return Ok(Json(with_request_context(
                    cached,
                    request_id,
                    ctx.idempotency_key.as_deref(),
                )));
            }
            record_summary_cache_miss(&state).await;
            let payload = fetch_summary_payload(
                &state,
                strategy_base,
                request_id,
                ctx.idempotency_key.as_deref(),
                &summary_request,
            )
            .await;
            write_summary_cache(&state, cache_key, payload.clone()).await;
            Ok(Json(with_request_context(
                payload,
                request_id,
                ctx.idempotency_key.as_deref(),
            )))
        }
    }
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

async fn fetch_summary_payload(
    state: &AppState,
    strategy_base: &str,
    request_id: &str,
    idempotency_key: Option<&str>,
    summary_request: &params::SummaryRequest,
) -> serde_json::Value {
    if let Some(aggregated_payload) = fetch_strategy_summary_aggregate(
        state,
        strategy_base,
        request_id,
        idempotency_key,
        summary_request,
    )
    .await
    {
        aggregated_payload
    } else {
        fetch_strategy_summary_fanout(
            state,
            strategy_base,
            request_id,
            idempotency_key,
            summary_request,
        )
        .await
    }
}

async fn record_summary_cache_hit(state: &AppState) {
    let mut metrics = state.metrics.write().await;
    metrics.strategy_summary_cache_hits += 1;
}

async fn record_summary_cache_miss(state: &AppState) {
    let mut metrics = state.metrics.write().await;
    metrics.strategy_summary_cache_misses += 1;
}

async fn record_summary_coalesced_wait(state: &AppState) {
    let mut metrics = state.metrics.write().await;
    metrics.strategy_summary_coalesced_waits += 1;
}
