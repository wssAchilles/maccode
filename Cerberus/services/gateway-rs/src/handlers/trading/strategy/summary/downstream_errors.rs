use axum::http::StatusCode;

use crate::handlers::trading::strategy::upstream::StrategyUpstreamError;

pub(super) fn render_upstream_send_error(
    err: StrategyUpstreamError,
    url: &str,
    request_id: &str,
) -> serde_json::Value {
    match err {
        StrategyUpstreamError::CircuitOpen { retry_after_ms } => serde_json::json!({
            "ok": false,
            "status_code": StatusCode::SERVICE_UNAVAILABLE.as_u16(),
            "url": url,
            "retry_after_ms": retry_after_ms,
            "error": structured_error(
                "upstream_circuit_open",
                format!("strategy upstream circuit open, retry after {retry_after_ms}ms"),
                request_id
            )
        }),
        StrategyUpstreamError::QueueSaturated { waited_ms } => serde_json::json!({
            "ok": false,
            "status_code": StatusCode::TOO_MANY_REQUESTS.as_u16(),
            "url": url,
            "error": structured_error(
                "upstream_queue_saturated",
                format!("strategy upstream queue saturated, waited {waited_ms}ms"),
                request_id
            )
        }),
        StrategyUpstreamError::AuthFailed(reason) => serde_json::json!({
            "ok": false,
            "status_code": StatusCode::BAD_GATEWAY.as_u16(),
            "url": url,
            "error": structured_error("upstream_auth_failed", reason, request_id)
        }),
        StrategyUpstreamError::RequestFailed(reason) => serde_json::json!({
            "ok": false,
            "status_code": StatusCode::BAD_GATEWAY.as_u16(),
            "url": url,
            "error": structured_error("upstream_request_failed", reason, request_id)
        }),
    }
}

pub(super) fn structured_error(
    code: &str,
    message: impl Into<String>,
    request_id: &str,
) -> serde_json::Value {
    serde_json::json!({
        "code": code,
        "message": message.into(),
        "request_id": request_id
    })
}

pub(super) fn normalize_downstream_error(
    payload: &serde_json::Value,
    status: StatusCode,
    fallback_request_id: &str,
) -> serde_json::Value {
    if let Some(error) = payload.get("error").and_then(|value| value.as_object()) {
        let code = error
            .get("code")
            .and_then(|value| value.as_str())
            .filter(|value| !value.is_empty())
            .unwrap_or_else(|| default_error_code(status));
        let message = error
            .get("message")
            .and_then(|value| value.as_str())
            .filter(|value| !value.is_empty())
            .unwrap_or_else(|| default_error_message(status));
        let request_id = error
            .get("request_id")
            .and_then(|value| value.as_str())
            .filter(|value| !value.is_empty())
            .or_else(|| {
                payload
                    .get("request_id")
                    .and_then(|value| value.as_str())
                    .filter(|value| !value.is_empty())
            })
            .unwrap_or(fallback_request_id);
        return structured_error(code, message.to_string(), request_id);
    }

    if let Some(message) = payload
        .get("detail")
        .and_then(|value| value.as_str())
        .filter(|value| !value.is_empty())
    {
        return structured_error(
            default_error_code(status),
            message.to_string(),
            fallback_request_id,
        );
    }

    structured_error(
        default_error_code(status),
        default_error_message(status).to_string(),
        fallback_request_id,
    )
}

fn default_error_code(status: StatusCode) -> &'static str {
    if status.is_server_error() {
        "upstream_internal_error"
    } else if status.is_client_error() {
        "upstream_request_error"
    } else {
        "upstream_error"
    }
}

fn default_error_message(status: StatusCode) -> &'static str {
    if status == StatusCode::REQUEST_TIMEOUT {
        "request timeout"
    } else {
        "request failed"
    }
}
