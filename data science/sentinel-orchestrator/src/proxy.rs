use axum::{
    Json,
    body::Body,
    http::{Response as HttpResponse, StatusCode, header},
    response::{IntoResponse, Response},
};
use reqwest::Method;
use serde_json::{Value, json};
use std::collections::HashMap;
use tracing::warn;

use crate::config::AppState;

pub async fn proxy_empty_post(state: &AppState, path: String) -> (StatusCode, Json<Value>) {
    proxy_request_json(state, Method::POST, path, None, None).await
}

pub async fn proxy_json_post(
    state: &AppState,
    path: String,
    payload: Value,
) -> (StatusCode, Json<Value>) {
    proxy_request_json(state, Method::POST, path, Some(payload), None).await
}

pub async fn proxy_json_post_with_headers(
    state: &AppState,
    path: String,
    payload: Value,
    headers: HashMap<String, String>,
) -> (StatusCode, Json<Value>) {
    proxy_request_json(state, Method::POST, path, Some(payload), Some(headers)).await
}

pub async fn proxy_json_patch(
    state: &AppState,
    path: String,
    payload: Value,
) -> (StatusCode, Json<Value>) {
    proxy_request_json(state, Method::PATCH, path, Some(payload), None).await
}

pub async fn proxy_get(state: &AppState, path: String) -> (StatusCode, Json<Value>) {
    proxy_request_json(state, Method::GET, path, None, None).await
}

pub async fn proxy_sse_get(state: &AppState, path: String) -> Response {
    let Some(base_url) = state.config.python_worker_base_url.as_ref() else {
        warn!("python worker base url not configured for {}", path);
        return unavailable_response().into_response();
    };

    let url = format!("{base_url}{path}");
    let request = state
        .http_client
        .get(&url)
        .header(header::ACCEPT, "text/event-stream")
        .header("X-Internal-Job-Token", &state.config.internal_job_token);

    match request.send().await {
        Ok(response) => {
            let status = response.status();
            let builder = HttpResponse::builder()
                .status(status)
                .header(header::CONTENT_TYPE, "text/event-stream")
                .header(header::CACHE_CONTROL, "no-cache")
                .header("x-accel-buffering", "no");
            match builder.body(Body::from_stream(response.bytes_stream())) {
                Ok(stream_response) => stream_response,
                Err(error) => {
                    warn!("failed to build SSE proxy response for {}: {}", url, error);
                    bad_gateway_response(
                        "UPSTREAM_BAD_RESPONSE",
                        format!("Failed to proxy SSE response from {url}"),
                    )
                    .into_response()
                }
            }
        }
        Err(error) => {
            warn!("failed to contact {}: {}", url, error);
            bad_gateway_response(
                "UPSTREAM_UNAVAILABLE",
                format!("Failed to reach python worker at {url}"),
            )
            .into_response()
        }
    }
}

async fn proxy_request_json(
    state: &AppState,
    method: Method,
    path: String,
    payload: Option<Value>,
    extra_headers: Option<HashMap<String, String>>,
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
                Ok(body) => (status, Json(body)),
                Err(error) => {
                    warn!("failed to decode response from {}: {}", url, error);
                    bad_gateway_response(
                        "UPSTREAM_BAD_RESPONSE",
                        format!("Failed to decode upstream response from {url}"),
                    )
                }
            }
        }
        Err(error) => {
            warn!("failed to contact {}: {}", url, error);
            bad_gateway_response(
                "UPSTREAM_UNAVAILABLE",
                format!("Failed to reach python worker at {url}"),
            )
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

fn bad_gateway_response(code: &str, message: String) -> (StatusCode, Json<Value>) {
    (
        StatusCode::BAD_GATEWAY,
        Json(json!({
            "success": false,
            "error": {
                "code": code,
                "message": message,
            }
        })),
    )
}
