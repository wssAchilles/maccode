pub(super) fn payload_matches(payload: &serde_json::Value, keys: &[&str], expected: &str) -> bool {
    payload_text(payload, keys).is_some_and(|value| value == expected)
}

pub(super) fn payload_matches_ci(
    payload: &serde_json::Value,
    keys: &[&str],
    expected: &str,
) -> bool {
    payload_text(payload, keys).is_some_and(|value| value.eq_ignore_ascii_case(expected))
}

fn payload_text(payload: &serde_json::Value, keys: &[&str]) -> Option<String> {
    if let Some(value) = payload_lookup(payload, keys) {
        return Some(value);
    }

    for nested in ["payload", "order", "execution", "error"] {
        if let Some(value) = payload
            .get(nested)
            .and_then(|child| payload_lookup(child, keys))
        {
            return Some(value);
        }
    }

    None
}

fn payload_lookup(payload: &serde_json::Value, keys: &[&str]) -> Option<String> {
    keys.iter()
        .find_map(|key| payload.get(*key).and_then(|value| value.as_str()))
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string)
}

#[cfg(test)]
mod tests {
    use super::{payload_matches, payload_matches_ci, payload_text};

    #[test]
    fn payload_text_reads_nested_execution_fields() {
        let payload = serde_json::json!({
            "execution": {
                "order_id": "ord-1",
                "symbol": "BTCUSDT"
            }
        });
        assert_eq!(
            payload_text(&payload, &["order_id"]).as_deref(),
            Some("ord-1")
        );
        assert_eq!(
            payload_text(&payload, &["symbol"]).as_deref(),
            Some("BTCUSDT")
        );
    }

    #[test]
    fn payload_matches_supports_case_insensitive_status() {
        let payload = serde_json::json!({
            "status": "submitted",
            "request_id": "rid-1"
        });
        assert!(payload_matches_ci(&payload, &["status"], "SUBMITTED"));
        assert!(payload_matches(&payload, &["request_id"], "rid-1"));
    }
}
