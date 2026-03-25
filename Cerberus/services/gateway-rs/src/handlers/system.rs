mod auth;
mod metrics;
mod readiness;

use axum::{
    extract::{Request, State},
    http::{header::CONTENT_TYPE, HeaderMap, HeaderValue},
    middleware::Next,
    response::{IntoResponse, Response},
    Json,
};

use crate::gateway_types::{AppState, RequestContext, SERVICE_NAME, SERVICE_VERSION};
use crate::gateway_utils::{extract_or_generate_request_id, set_request_id_header};

pub(crate) async fn request_context_middleware(mut request: Request, next: Next) -> Response {
    let request_id = extract_or_generate_request_id(request.headers());
    request.extensions_mut().insert(RequestContext {
        request_id: request_id.clone(),
    });

    let mut response = next.run(request).await;
    set_request_id_header(response.headers_mut(), &request_id);
    response
}

pub(crate) async fn health() -> impl IntoResponse {
    Json(serde_json::json!({
        "status": "ok",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION
    }))
}

pub(crate) async fn ready(State(state): State<AppState>) -> impl IntoResponse {
    let metrics = state.metrics.read().await.clone();
    let (status, payload) = readiness::build_ready_payload(&state, &metrics);
    (status, Json(payload))
}

pub(crate) async fn get_metrics_json(State(state): State<AppState>) -> impl IntoResponse {
    let metrics = state.metrics.read().await.clone();
    let tracked_symbols = state.latest_by_symbol.read().await.len();
    Json(metrics::build_metrics_json(&state, &metrics, tracked_symbols))
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

pub(crate) use auth::require_firebase_auth;
