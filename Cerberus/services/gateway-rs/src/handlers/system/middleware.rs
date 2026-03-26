use std::time::Instant;

use axum::{
    extract::{Request, State},
    middleware::Next,
    response::Response,
};

use crate::gateway_types::{AppState, RequestContext};
use crate::gateway_utils::{
    extract_idempotency_key, extract_or_generate_request_id, set_idempotency_key_header,
    set_request_id_header,
};

pub(crate) async fn request_context_middleware(
    State(state): State<AppState>,
    mut request: Request,
    next: Next,
) -> Response {
    let started = Instant::now();
    let request_id = extract_or_generate_request_id(request.headers());
    let idempotency_key = extract_idempotency_key(request.headers());
    request.extensions_mut().insert(RequestContext {
        request_id: request_id.clone(),
        idempotency_key: idempotency_key.clone(),
    });

    let mut response = next.run(request).await;
    let latency_ms = started.elapsed().as_millis() as u64;
    let is_client_error = response.status().is_client_error();
    let is_server_error = response.status().is_server_error();
    record_http_metrics(&state, is_client_error, is_server_error, latency_ms).await;
    set_request_id_header(response.headers_mut(), &request_id);
    set_idempotency_key_header(response.headers_mut(), idempotency_key.as_deref());
    response
}

async fn record_http_metrics(
    state: &AppState,
    is_client_error: bool,
    is_server_error: bool,
    latency_ms: u64,
) {
    const MAX_SAMPLES: usize = 1024;
    let mut metrics = state.metrics.write().await;
    metrics.http_requests_total += 1;
    if is_client_error {
        metrics.http_requests_4xx += 1;
    }
    if is_server_error {
        metrics.http_requests_5xx += 1;
    }
    metrics.last_http_latency_ms = Some(latency_ms);
    metrics.http_latency_samples_ms.push_back(latency_ms);
    while metrics.http_latency_samples_ms.len() > MAX_SAMPLES {
        metrics.http_latency_samples_ms.pop_front();
    }
}
