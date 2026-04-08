use axum::{http::StatusCode, Json};

use super::GatewayErrorCode;

#[allow(dead_code)]
pub(crate) fn success_body(
    data: serde_json::Value,
    request_id: &str,
    idempotency_key: Option<&str>,
) -> Json<serde_json::Value> {
    Json(api_envelope(request_id, Some(data), None, idempotency_key))
}

pub(crate) fn error_body(
    code: &str,
    message: impl Into<String>,
    request_id: &str,
) -> Json<serde_json::Value> {
    Json(api_envelope(
        request_id,
        None,
        Some(serde_json::json!({
            "code": code,
            "message": message.into(),
        })),
        None,
    ))
}

pub(crate) fn error_body_value(
    error: serde_json::Value,
    request_id: &str,
) -> Json<serde_json::Value> {
    Json(api_envelope(request_id, None, Some(error), None))
}

pub(crate) fn error_body_code(
    code: GatewayErrorCode,
    message: impl Into<String>,
    request_id: &str,
) -> Json<serde_json::Value> {
    error_body(code.as_str(), message, request_id)
}

pub(crate) fn internal_err_json(
    request_id: &str,
    code: &str,
    err: impl std::fmt::Display,
) -> (StatusCode, Json<serde_json::Value>) {
    (
        StatusCode::INTERNAL_SERVER_ERROR,
        error_body(code, err.to_string(), request_id),
    )
}

#[allow(dead_code)]
pub(crate) fn with_request_id(payload: serde_json::Value, request_id: &str) -> serde_json::Value {
    api_envelope(request_id, Some(payload), None, None)
}

pub(crate) fn with_request_context(
    payload: serde_json::Value,
    request_id: &str,
    idempotency_key: Option<&str>,
) -> serde_json::Value {
    api_envelope(request_id, Some(payload), None, idempotency_key)
}

fn api_envelope(
    request_id: &str,
    data: Option<serde_json::Value>,
    error: Option<serde_json::Value>,
    idempotency_key: Option<&str>,
) -> serde_json::Value {
    let mut envelope = serde_json::json!({
        "request_id": request_id,
        "data": data.unwrap_or(serde_json::Value::Null),
        "error": error.unwrap_or(serde_json::Value::Null),
    });
    if let Some(key) = idempotency_key {
        if let Some(object) = envelope.as_object_mut() {
            object.insert(
                "idempotency_key".to_string(),
                serde_json::Value::String(key.to_string()),
            );
        }
    }
    envelope
}

#[cfg(test)]
mod tests {
    use super::{error_body_value, with_request_context, with_request_id};

    #[test]
    fn wraps_payload_into_api_envelope() {
        let payload = serde_json::json!({
            "status": "ok"
        });
        let updated = with_request_id(payload, "rid-123");
        assert_eq!(updated["request_id"], serde_json::json!("rid-123"));
        assert_eq!(updated["error"], serde_json::Value::Null);
        assert_eq!(updated["data"]["status"], serde_json::json!("ok"));
    }

    #[test]
    fn preserves_payload_request_id_inside_data() {
        let payload = serde_json::json!({
            "request_id": "rid-existing"
        });
        let updated = with_request_id(payload, "rid-new");
        assert_eq!(updated["request_id"], serde_json::json!("rid-new"));
        assert_eq!(
            updated["data"]["request_id"],
            serde_json::json!("rid-existing")
        );
    }

    #[test]
    fn includes_idempotency_key_when_present() {
        let payload = serde_json::json!({ "ok": true });
        let updated = with_request_context(payload, "rid-9", Some("idem-1"));
        assert_eq!(updated["idempotency_key"], serde_json::json!("idem-1"));
    }

    #[test]
    fn wraps_structured_error_without_dropping_fields() {
        let error = serde_json::json!({
            "code": "validation_error",
            "message": "validation failed",
            "request_id": "rid-strategy-422",
            "details": [
                {
                    "loc": ["body", "symbol"],
                    "msg": "Field required"
                }
            ]
        });

        let wrapped = error_body_value(error, "rid-gateway-001").0;

        assert_eq!(wrapped["request_id"], serde_json::json!("rid-gateway-001"));
        assert_eq!(wrapped["error"]["request_id"], serde_json::json!("rid-strategy-422"));
        assert_eq!(
            wrapped["error"]["details"][0]["loc"],
            serde_json::json!(["body", "symbol"])
        );
    }
}
