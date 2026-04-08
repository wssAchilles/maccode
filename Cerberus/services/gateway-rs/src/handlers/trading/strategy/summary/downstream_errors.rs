use axum::http::StatusCode;

use crate::handlers::trading::strategy::summary::model::SummaryComponentEnvelope;
use crate::handlers::trading::strategy::upstream::StrategyUpstreamError;

pub(super) fn render_upstream_send_error(
    err: StrategyUpstreamError,
    url: &str,
    request_id: &str,
) -> SummaryComponentEnvelope {
    match err {
        StrategyUpstreamError::CircuitOpen { retry_after_ms } => SummaryComponentEnvelope {
            ok: false,
            status_code: StatusCode::SERVICE_UNAVAILABLE.as_u16(),
            url: Some(url.to_string()),
            payload: None,
            retry_after_ms: Some(retry_after_ms),
            error: Some(structured_error(
                "upstream_circuit_open",
                format!("strategy upstream circuit open, retry after {retry_after_ms}ms"),
                request_id,
            )),
        },
        StrategyUpstreamError::QueueSaturated { waited_ms } => SummaryComponentEnvelope {
            ok: false,
            status_code: StatusCode::TOO_MANY_REQUESTS.as_u16(),
            url: Some(url.to_string()),
            payload: None,
            retry_after_ms: None,
            error: Some(structured_error(
                "upstream_queue_saturated",
                format!("strategy upstream queue saturated, waited {waited_ms}ms"),
                request_id,
            )),
        },
        StrategyUpstreamError::AuthFailed(reason) => SummaryComponentEnvelope {
            ok: false,
            status_code: StatusCode::BAD_GATEWAY.as_u16(),
            url: Some(url.to_string()),
            payload: None,
            retry_after_ms: None,
            error: Some(structured_error("upstream_auth_failed", reason, request_id)),
        },
        StrategyUpstreamError::RequestFailed(reason) => SummaryComponentEnvelope {
            ok: false,
            status_code: StatusCode::BAD_GATEWAY.as_u16(),
            url: Some(url.to_string()),
            payload: None,
            retry_after_ms: None,
            error: Some(structured_error(
                "upstream_request_failed",
                reason,
                request_id,
            )),
        },
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

pub(crate) fn normalize_downstream_error(
    payload: &serde_json::Value,
    status: StatusCode,
    fallback_request_id: &str,
) -> serde_json::Value {
    if let Some(error) = payload.get("error").and_then(|value| value.as_object()) {
        let mut normalized = error.clone();
        let code = error
            .get("code")
            .and_then(|value| value.as_str())
            .filter(|value| !value.is_empty())
            .unwrap_or_else(|| default_error_code(status));
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
        normalized.insert(
            "code".to_string(),
            serde_json::Value::String(code.to_string()),
        );
        normalized.insert(
            "message".to_string(),
            normalized_message_value(error.get("message"), status),
        );
        normalized.insert(
            "request_id".to_string(),
            serde_json::Value::String(request_id.to_string()),
        );
        return serde_json::Value::Object(normalized);
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

fn normalized_message_value(
    message: Option<&serde_json::Value>,
    status: StatusCode,
) -> serde_json::Value {
    match message {
        Some(serde_json::Value::String(value)) if !value.is_empty() => {
            serde_json::Value::String(value.clone())
        }
        Some(value) if !value.is_null() => serde_json::Value::String(value.to_string()),
        _ => serde_json::Value::String(default_error_message(status).to_string()),
    }
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

#[cfg(test)]
mod tests {
    use super::normalize_downstream_error;
    use axum::http::StatusCode;

    #[test]
    fn normalize_downstream_error_preserves_structured_details() {
        let payload = serde_json::json!({
            "error": {
                "code": "validation_error",
                "message": "validation failed",
                "request_id": "rid-strategy-422",
                "details": [
                    {
                        "loc": ["body", "symbol"],
                        "msg": "Field required",
                        "type": "missing"
                    }
                ]
            }
        });

        let normalized = normalize_downstream_error(
            &payload,
            StatusCode::UNPROCESSABLE_ENTITY,
            "rid-gateway-001",
        );

        assert_eq!(normalized["code"], serde_json::json!("validation_error"));
        assert_eq!(normalized["message"], serde_json::json!("validation failed"));
        assert_eq!(normalized["request_id"], serde_json::json!("rid-strategy-422"));
        assert_eq!(
            normalized["details"][0]["loc"],
            serde_json::json!(["body", "symbol"])
        );
    }
}
