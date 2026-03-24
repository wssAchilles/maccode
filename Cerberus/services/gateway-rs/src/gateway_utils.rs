mod channel;
mod crypto;
mod http;
mod misc;
mod parsing;
mod request_id;

pub(crate) use channel::*;
pub(crate) use crypto::*;
pub(crate) use http::*;
pub(crate) use misc::*;
pub(crate) use parsing::*;
pub(crate) use request_id::*;

#[cfg(test)]
mod tests {
    use axum::http::{HeaderMap, HeaderValue};

    use crate::gateway_types::REQUEST_ID_HEADER;

    use super::*;

    #[test]
    fn test_binance_exchange_info_path_switch() {
        assert_eq!(
            binance_exchange_info_path("/api/v3/order/test"),
            "/api/v3/exchangeInfo"
        );
        assert_eq!(
            binance_exchange_info_path("/fapi/v1/order/test"),
            "/fapi/v1/exchangeInfo"
        );
    }

    #[test]
    fn test_parse_positive_number() {
        assert!(parse_positive_number("qty", "0.01").is_ok());
        assert!(parse_positive_number("qty", "0").is_err());
        assert!(parse_positive_number("qty", "-1").is_err());
        assert!(parse_positive_number("qty", "abc").is_err());
    }

    #[test]
    fn test_symbol_allowed() {
        assert!(symbol_allowed("BTCUSDT", &[]));
        assert!(symbol_allowed("BTCUSDT", &["BTCUSDT".to_string()]));
        assert!(!symbol_allowed("BTCUSDT", &["ETHUSDT".to_string()]));
    }

    #[test]
    fn test_sanitize_request_id() {
        assert_eq!(
            sanitize_request_id("req-001_abc.DEF"),
            Some("req-001_abc.DEF".to_string())
        );
        assert_eq!(sanitize_request_id(""), None);
        assert_eq!(sanitize_request_id("   "), None);
        assert_eq!(sanitize_request_id("bad/id"), None);
    }

    #[test]
    fn test_extract_or_generate_request_id() {
        let mut headers = HeaderMap::new();
        headers.insert(REQUEST_ID_HEADER, HeaderValue::from_static("rid-123"));
        assert_eq!(extract_or_generate_request_id(&headers), "rid-123");

        headers.insert(REQUEST_ID_HEADER, HeaderValue::from_static("bad/id"));
        let generated = extract_or_generate_request_id(&headers);
        assert!(!generated.is_empty());
        assert_ne!(generated, "bad/id");
    }

    #[test]
    fn test_escape_prometheus_label() {
        assert_eq!(
            escape_prometheus_label("gateway\"x\\y\nz"),
            "gateway\\\"x\\\\y\\nz".to_string()
        );
    }
}
