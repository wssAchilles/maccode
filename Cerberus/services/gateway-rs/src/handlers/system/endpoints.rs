use axum::{
    extract::{Extension, State},
    http::{header::CONTENT_TYPE, HeaderMap, HeaderValue},
    response::IntoResponse,
    Json,
};

use crate::gateway_types::{AppState, RequestContext, SERVICE_NAME, SERVICE_VERSION};
use crate::handlers::common::with_request_context;

use super::{metrics, readiness};

pub(crate) async fn health(Extension(ctx): Extension<RequestContext>) -> impl IntoResponse {
    Json(with_request_context(
        serde_json::json!({
            "status": "ok",
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION
        }),
        ctx.request_id.as_str(),
        ctx.idempotency_key.as_deref(),
    ))
}

pub(crate) async fn ready(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
) -> impl IntoResponse {
    let metrics = state.metrics.read().await.clone();
    let (status, payload) = readiness::build_ready_payload(&state, &metrics);
    (
        status,
        Json(with_request_context(
            payload,
            ctx.request_id.as_str(),
            ctx.idempotency_key.as_deref(),
        )),
    )
}

pub(crate) async fn get_metrics_json(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
) -> impl IntoResponse {
    let metrics = state.metrics.read().await.clone();
    let tracked_symbols = state.latest_by_symbol.read().await.len();
    Json(with_request_context(
        metrics::build_metrics_json(&state, &metrics, tracked_symbols),
        ctx.request_id.as_str(),
        ctx.idempotency_key.as_deref(),
    ))
}

pub(crate) async fn get_metrics(State(state): State<AppState>) -> impl IntoResponse {
    let metrics = state.metrics.read().await.clone();
    let tracked_symbols = state.latest_by_symbol.read().await.len();
    let body = metrics::build_prometheus_body(&state, &metrics, tracked_symbols);

    let mut headers = HeaderMap::new();
    headers.insert(
        CONTENT_TYPE,
        HeaderValue::from_static("text/plain; version=0.0.4; charset=utf-8"),
    );
    (headers, body)
}
