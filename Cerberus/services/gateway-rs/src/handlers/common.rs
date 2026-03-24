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
