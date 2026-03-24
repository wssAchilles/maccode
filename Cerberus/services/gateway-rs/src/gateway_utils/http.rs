use axum::http::StatusCode;

use crate::gateway_types::DEFAULT_BINANCE_ORDER_TEST_PATH;

pub(crate) fn normalize_http_path(path: &str) -> String {
    let trimmed = path.trim();
    if trimmed.is_empty() {
        return DEFAULT_BINANCE_ORDER_TEST_PATH.to_string();
    }
    if trimmed.starts_with('/') {
        return trimmed.to_string();
    }
    format!("/{trimmed}")
}

pub(crate) fn binance_exchange_info_path(order_test_path: &str) -> &'static str {
    let normalized = normalize_http_path(order_test_path);
    if normalized.starts_with("/api/") {
        "/api/v3/exchangeInfo"
    } else {
        "/fapi/v1/exchangeInfo"
    }
}

pub(crate) fn to_axum_status(status: reqwest::StatusCode) -> StatusCode {
    StatusCode::from_u16(status.as_u16()).unwrap_or(StatusCode::BAD_GATEWAY)
}
