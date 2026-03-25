use axum::http::{HeaderMap, HeaderValue};
use uuid::Uuid;

use crate::gateway_types::{IDEMPOTENCY_KEY_ALT_HEADER, IDEMPOTENCY_KEY_HEADER, REQUEST_ID_HEADER};

pub(crate) fn extract_or_generate_request_id(headers: &HeaderMap) -> String {
    if let Some(raw) = headers.get(REQUEST_ID_HEADER).and_then(|v| v.to_str().ok()) {
        if let Some(valid) = sanitize_request_id(raw) {
            return valid;
        }
    }
    Uuid::new_v4().to_string()
}

pub(crate) fn sanitize_request_id(raw: &str) -> Option<String> {
    let trimmed = raw.trim();
    if trimmed.is_empty() || trimmed.len() > 128 {
        return None;
    }
    if trimmed
        .chars()
        .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '-' | '_' | '.'))
    {
        Some(trimmed.to_string())
    } else {
        None
    }
}

pub(crate) fn set_request_id_header(headers: &mut HeaderMap, request_id: &str) {
    if let Ok(value) = HeaderValue::from_str(request_id) {
        headers.insert(REQUEST_ID_HEADER, value);
    }
}

pub(crate) fn extract_idempotency_key(headers: &HeaderMap) -> Option<String> {
    let raw = headers
        .get(IDEMPOTENCY_KEY_HEADER)
        .or_else(|| headers.get(IDEMPOTENCY_KEY_ALT_HEADER))
        .and_then(|value| value.to_str().ok())?;
    sanitize_idempotency_key(raw)
}

pub(crate) fn sanitize_idempotency_key(raw: &str) -> Option<String> {
    let trimmed = raw.trim();
    if trimmed.is_empty() || trimmed.len() > 128 {
        return None;
    }
    if trimmed
        .chars()
        .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '-' | '_' | '.' | ':'))
    {
        Some(trimmed.to_string())
    } else {
        None
    }
}

pub(crate) fn set_idempotency_key_header(headers: &mut HeaderMap, idempotency_key: Option<&str>) {
    let Some(key) = idempotency_key else {
        return;
    };
    if let Ok(value) = HeaderValue::from_str(key) {
        headers.insert(IDEMPOTENCY_KEY_ALT_HEADER, value.clone());
        headers.insert(IDEMPOTENCY_KEY_HEADER, value);
    }
}
