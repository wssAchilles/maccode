use crate::gateway_types::API_ENVELOPE_SCHEMA_VERSION;
use crate::gateway_utils::current_millis;
use uuid::Uuid;

pub(super) fn normalize_order_payload(
    channel: &str,
    payload: serde_json::Value,
) -> serde_json::Value {
    if is_event_envelope(&payload) {
        return payload;
    }
    build_event_envelope(channel, payload)
}

fn is_event_envelope(payload: &serde_json::Value) -> bool {
    payload.as_object().is_some_and(|object| {
        object.contains_key("event_type")
            && object.contains_key("event_id")
            && object.contains_key("created_at")
            && object.contains_key("schema_version")
            && object.contains_key("payload")
    })
}

fn build_event_envelope(channel: &str, payload: serde_json::Value) -> serde_json::Value {
    let event_type = infer_event_type(channel, &payload);
    let correlation_id = infer_correlation_id(&payload);
    serde_json::json!({
        "event_type": event_type,
        "event_id": format!("evt-{}", Uuid::new_v4()),
        "created_at": current_millis(),
        "schema_version": API_ENVELOPE_SCHEMA_VERSION,
        "correlation_id": correlation_id,
        "payload": payload
    })
}

fn infer_event_type(channel: &str, payload: &serde_json::Value) -> String {
    payload
        .get("event")
        .or_else(|| payload.get("type"))
        .and_then(|value| value.as_str())
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .unwrap_or(channel)
        .to_string()
}

fn infer_correlation_id(payload: &serde_json::Value) -> Option<String> {
    payload
        .get("request_id")
        .or_else(|| payload.get("correlation_id"))
        .and_then(|value| value.as_str())
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string)
}
