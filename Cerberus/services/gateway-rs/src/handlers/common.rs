use axum::{http::StatusCode, Json};

pub(crate) fn error_body(
    code: &str,
    message: impl Into<String>,
    request_id: &str,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "error": {
            "code": code,
            "message": message.into(),
            "request_id": request_id
        }
    }))
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

pub(crate) fn with_request_id(
    mut payload: serde_json::Value,
    request_id: &str,
) -> serde_json::Value {
    if let Some(object) = payload.as_object_mut() {
        object
            .entry("request_id".to_string())
            .or_insert_with(|| serde_json::Value::String(request_id.to_string()));
    }
    payload
}

#[cfg(test)]
mod tests {
    use super::with_request_id;

    #[test]
    fn injects_request_id_into_json_object() {
        let payload = serde_json::json!({
            "status": "ok"
        });
        let updated = with_request_id(payload, "rid-123");
        assert_eq!(updated["request_id"], serde_json::json!("rid-123"));
        assert_eq!(updated["status"], serde_json::json!("ok"));
    }

    #[test]
    fn keeps_existing_request_id() {
        let payload = serde_json::json!({
            "request_id": "rid-existing"
        });
        let updated = with_request_id(payload, "rid-new");
        assert_eq!(updated["request_id"], serde_json::json!("rid-existing"));
    }
}
