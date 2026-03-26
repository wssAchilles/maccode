use axum::{http::StatusCode, Json};

use crate::handlers::common::{error_body, error_body_code, GatewayErrorCode};

pub(crate) type AuthRejection = (StatusCode, Json<serde_json::Value>);

pub(super) fn auth_err(
    status: StatusCode,
    code: &str,
    message: impl Into<String>,
    request_id: &str,
) -> AuthRejection {
    if let Some(known) = to_known_code(code) {
        (status, error_body_code(known, message.into(), request_id))
    } else {
        (status, error_body(code, message.into(), request_id))
    }
}

fn to_known_code(code: &str) -> Option<GatewayErrorCode> {
    match code {
        "validation_error" => Some(GatewayErrorCode::ValidationError),
        "config_error" => Some(GatewayErrorCode::ConfigError),
        "upstream_error" => Some(GatewayErrorCode::UpstreamError),
        "upstream_request_failed" => Some(GatewayErrorCode::UpstreamRequestFailed),
        "upstream_decode_failed" => Some(GatewayErrorCode::UpstreamDecodeFailed),
        "upstream_status_error" => Some(GatewayErrorCode::UpstreamStatusError),
        "internal_error" => Some(GatewayErrorCode::InternalError),
        "auth_required" => Some(GatewayErrorCode::AuthRequired),
        "auth_verify_failed" => Some(GatewayErrorCode::AuthVerifyFailed),
        "signature_error" => Some(GatewayErrorCode::SignatureError),
        _ => None,
    }
}
