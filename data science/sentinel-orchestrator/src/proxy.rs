use async_stream::stream;
use axum::{
    Json,
    body::Body,
    http::{Response as HttpResponse, StatusCode, header},
    response::{IntoResponse, Response},
};
use bytes::Bytes;
use futures_util::TryStreamExt;
use reqwest::Method;
use serde_json::{Value, json};
use std::collections::HashMap;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio_util::io::StreamReader;
use tracing::warn;

use crate::upstream::{
    PYTHON_WORKER_KEY, UpstreamFailureKind, UpstreamFailureRecord, classify_reqwest_error,
};
use crate::{
    config::AppState,
    contract::{
        NormalizedSseFrame, NormalizedSseFrameKind, encode_sse_frame, normalize_upstream_sse_frame,
    },
    correlation::CORRELATION_ID_HEADER,
};

pub async fn proxy_empty_post(
    state: &AppState,
    path: String,
    correlation_id: Option<&str>,
) -> (StatusCode, Json<Value>) {
    proxy_request_json(state, Method::POST, path, None, None, correlation_id).await
}

pub async fn proxy_json_post(
    state: &AppState,
    path: String,
    payload: Value,
    correlation_id: Option<&str>,
) -> (StatusCode, Json<Value>) {
    proxy_request_json(
        state,
        Method::POST,
        path,
        Some(payload),
        None,
        correlation_id,
    )
    .await
}

pub async fn proxy_json_post_with_headers(
    state: &AppState,
    path: String,
    payload: Value,
    headers: HashMap<String, String>,
    correlation_id: Option<&str>,
) -> (StatusCode, Json<Value>) {
    proxy_request_json(
        state,
        Method::POST,
        path,
        Some(payload),
        Some(headers),
        correlation_id,
    )
    .await
}

pub async fn proxy_json_patch(
    state: &AppState,
    path: String,
    payload: Value,
    correlation_id: Option<&str>,
) -> (StatusCode, Json<Value>) {
    proxy_request_json(
        state,
        Method::PATCH,
        path,
        Some(payload),
        None,
        correlation_id,
    )
    .await
}

pub async fn proxy_get(
    state: &AppState,
    path: String,
    correlation_id: Option<&str>,
) -> (StatusCode, Json<Value>) {
    proxy_request_json(state, Method::GET, path, None, None, correlation_id).await
}

pub async fn proxy_sse_get(
    state: &AppState,
    path: String,
    operation_id: String,
    correlation_id: String,
) -> Response {
    let Some(base_url) = state.config.python_worker_base_url.as_ref() else {
        warn!("python worker base url not configured for {}", path);
        return unavailable_response().into_response();
    };

    let url = format!("{base_url}{path}");
    let request = state
        .http_client
        .get(&url)
        .header(header::ACCEPT, "text/event-stream")
        .header("X-Internal-Job-Token", &state.config.internal_job_token)
        .header(CORRELATION_ID_HEADER, &correlation_id);

    match request.send().await {
        Ok(response) => {
            let status = response.status();
            if !status.is_success() {
                let failure = UpstreamFailureRecord::new(
                    UpstreamFailureKind::BadStatus,
                    format!("Python worker returned non-success SSE status {status} for {url}"),
                )
                .with_status_code(status.as_u16());
                state
                    .worker_health_registry
                    .record_failure(PYTHON_WORKER_KEY, failure.clone())
                    .await;
                return bad_gateway_response(&failure).into_response();
            }

            state
                .worker_health_registry
                .record_success(PYTHON_WORKER_KEY)
                .await;
            let normalized_stream =
                build_normalized_sse_stream(response, correlation_id, operation_id);
            let builder = HttpResponse::builder()
                .status(status)
                .header(header::CONTENT_TYPE, "text/event-stream")
                .header(header::CACHE_CONTROL, "no-cache")
                .header("x-accel-buffering", "no");
            match builder.body(Body::from_stream(normalized_stream)) {
                Ok(stream_response) => stream_response,
                Err(error) => {
                    warn!("failed to build SSE proxy response for {}: {}", url, error);
                    let failure = UpstreamFailureRecord::new(
                        UpstreamFailureKind::SseProxyError,
                        format!("Failed to proxy SSE response from {url}: {error}"),
                    );
                    state
                        .worker_health_registry
                        .record_failure(PYTHON_WORKER_KEY, failure.clone())
                        .await;
                    bad_gateway_response(&failure).into_response()
                }
            }
        }
        Err(error) => {
            warn!("failed to contact {}: {}", url, error);
            let failure = UpstreamFailureRecord::new(
                classify_reqwest_error(&error, true),
                format!("Failed to reach python worker at {url}: {error}"),
            );
            state
                .worker_health_registry
                .record_failure(PYTHON_WORKER_KEY, failure.clone())
                .await;
            bad_gateway_response(&failure).into_response()
        }
    }
}

async fn proxy_request_json(
    state: &AppState,
    method: Method,
    path: String,
    payload: Option<Value>,
    extra_headers: Option<HashMap<String, String>>,
    correlation_id: Option<&str>,
) -> (StatusCode, Json<Value>) {
    let Some(base_url) = state.config.python_worker_base_url.as_ref() else {
        warn!("python worker base url not configured for {}", path);
        return unavailable_response();
    };

    let url = format!("{base_url}{path}");
    let mut request = state
        .http_client
        .request(method, &url)
        .header(header::CONTENT_TYPE, "application/json")
        .header("X-Internal-Job-Token", &state.config.internal_job_token);

    if let Some(correlation_id) = correlation_id {
        request = request.header(CORRELATION_ID_HEADER, correlation_id);
    }

    if let Some(headers) = extra_headers {
        for (key, value) in headers {
            request = request.header(&key, value);
        }
    }

    if let Some(body) = payload {
        request = request.json(&body);
    }

    match request.send().await {
        Ok(response) => {
            let status = response.status();
            match response.json::<Value>().await {
                Ok(body) => {
                    if status.is_success() {
                        state
                            .worker_health_registry
                            .record_success(PYTHON_WORKER_KEY)
                            .await;
                    } else {
                        let failure = UpstreamFailureRecord::new(
                            UpstreamFailureKind::BadStatus,
                            format!("Python worker returned non-success status {status} for {url}"),
                        )
                        .with_status_code(status.as_u16());
                        state
                            .worker_health_registry
                            .record_failure(PYTHON_WORKER_KEY, failure)
                            .await;
                    }
                    (status, Json(body))
                }
                Err(error) => {
                    warn!("failed to decode response from {}: {}", url, error);
                    let failure = UpstreamFailureRecord::new(
                        UpstreamFailureKind::DecodeError,
                        format!("Failed to decode upstream response from {url}: {error}"),
                    );
                    state
                        .worker_health_registry
                        .record_failure(PYTHON_WORKER_KEY, failure.clone())
                        .await;
                    bad_gateway_response(&failure)
                }
            }
        }
        Err(error) => {
            warn!("failed to contact {}: {}", url, error);
            let failure = UpstreamFailureRecord::new(
                classify_reqwest_error(&error, false),
                format!("Failed to reach python worker at {url}: {error}"),
            );
            state
                .worker_health_registry
                .record_failure(PYTHON_WORKER_KEY, failure.clone())
                .await;
            bad_gateway_response(&failure)
        }
    }
}

fn unavailable_response() -> (StatusCode, Json<Value>) {
    (
        StatusCode::SERVICE_UNAVAILABLE,
        Json(json!({
            "success": false,
            "error": {
                "code": "PYTHON_WORKER_UNAVAILABLE",
                "message": "PYTHON_WORKER_BASE_URL is not configured",
            }
        })),
    )
}

fn bad_gateway_response(failure: &UpstreamFailureRecord) -> (StatusCode, Json<Value>) {
    (
        StatusCode::BAD_GATEWAY,
        Json(json!({
            "success": false,
            "error": {
                "code": failure.kind.error_code(),
                "kind": failure.kind,
                "message": failure.message,
                "status_code": failure.status_code,
            }
        })),
    )
}

fn build_normalized_sse_stream(
    response: reqwest::Response,
    correlation_id: String,
    operation_id: String,
) -> impl futures_util::Stream<Item = Result<Bytes, std::io::Error>> {
    let byte_stream = response
        .bytes_stream()
        .map_err(|error| std::io::Error::other(error.to_string()));
    let reader = StreamReader::new(byte_stream);
    let mut lines = BufReader::new(reader).lines();

    stream! {
        let mut current_event: Option<String> = None;
        let mut current_id: Option<String> = None;
        let mut data_lines: Vec<String> = Vec::new();
        let mut saw_comment = false;
        let mut emitted_closed = false;

        loop {
            match lines.next_line().await {
                Ok(Some(line)) => {
                    if line.is_empty() {
                        if let Some((kind, frame)) = normalize_upstream_sse_frame(
                            current_event.as_deref(),
                            current_id.as_deref(),
                            &data_lines,
                            saw_comment,
                            &correlation_id,
                            &operation_id,
                        ) {
                            if kind == NormalizedSseFrameKind::Closed {
                                emitted_closed = true;
                            }
                            yield Ok(Bytes::from(frame));
                        }
                        current_event = None;
                        current_id = None;
                        data_lines.clear();
                        saw_comment = false;
                        continue;
                    }

                    if line.starts_with(':') {
                        saw_comment = true;
                        continue;
                    }

                    if let Some(value) = line.strip_prefix("event:") {
                        current_event = Some(value.trim().to_string());
                        continue;
                    }

                    if let Some(value) = line.strip_prefix("id:") {
                        current_id = Some(value.trim().to_string());
                        continue;
                    }

                    if let Some(value) = line.strip_prefix("data:") {
                        data_lines.push(value.trim_start().to_string());
                    }
                }
                Ok(None) => {
                    if let Some((kind, frame)) = normalize_upstream_sse_frame(
                        current_event.as_deref(),
                        current_id.as_deref(),
                        &data_lines,
                        saw_comment,
                        &correlation_id,
                        &operation_id,
                    ) {
                        if kind == NormalizedSseFrameKind::Closed {
                            emitted_closed = true;
                        }
                        yield Ok(Bytes::from(frame));
                    }

                    if !emitted_closed {
                        let frame = NormalizedSseFrame {
                            frame_type: NormalizedSseFrameKind::Closed,
                            correlation_id: correlation_id.clone(),
                            operation_id: operation_id.clone(),
                            event_id: None,
                            event_type: Some("upstream.eof".to_string()),
                            payload: Some(json!({
                                "operation_id": operation_id,
                                "reason": "upstream_eof",
                            })),
                            error: None,
                        };
                        yield Ok(Bytes::from(encode_sse_frame(&frame)));
                    }
                    break;
                }
                Err(error) => {
                    let frame = NormalizedSseFrame {
                        frame_type: NormalizedSseFrameKind::Error,
                        correlation_id: correlation_id.clone(),
                        operation_id: operation_id.clone(),
                        event_id: None,
                        event_type: Some("upstream.read_error".to_string()),
                        payload: None,
                        error: Some(json!({
                            "code": "UPSTREAM_SSE_READ_ERROR",
                            "message": error.to_string(),
                        })),
                    };
                    yield Ok(Bytes::from(encode_sse_frame(&frame)));
                    break;
                }
            }
        }
    }
}
