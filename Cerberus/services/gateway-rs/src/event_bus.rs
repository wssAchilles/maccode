use crate::gateway_types::{
    AppState, OrderEvent, API_ENVELOPE_SCHEMA_VERSION, MAX_RECENT_ORDER_EVENTS,
};
use crate::gateway_utils::current_millis;
use uuid::Uuid;

pub(crate) async fn publish_order_event(
    state: &AppState,
    channel: String,
    payload: serde_json::Value,
) {
    let normalized_payload = normalize_order_payload(&channel, payload);
    let event = OrderEvent {
        channel,
        payload: normalized_payload,
        received_at: current_millis(),
    };

    let _ = state.orders_tx.send(event.clone());
    {
        let mut recent = state.recent_order_events.write().await;
        recent.push_back(event);
        if recent.len() > MAX_RECENT_ORDER_EVENTS {
            recent.pop_front();
        }
    }
    {
        let mut metrics = state.metrics.write().await;
        metrics.order_events += 1;
        metrics.last_order_event_at = Some(current_millis());
        metrics.last_order_ingest_error = None;
    }
}

pub(crate) fn event_matches_account(event: &OrderEvent, account_id: &str) -> bool {
    if event.channel.ends_with(&format!(".{account_id}")) {
        return true;
    }

    let payload = payload_for_matching(&event.payload);
    ["account_id", "maker_account_id", "taker_account_id"]
        .iter()
        .any(|key| {
            payload
                .get(key)
                .and_then(|value| value.as_str())
                .is_some_and(|value| value == account_id)
        })
}

fn normalize_order_payload(channel: &str, payload: serde_json::Value) -> serde_json::Value {
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

fn payload_for_matching<'a>(payload: &'a serde_json::Value) -> &'a serde_json::Value {
    payload
        .get("payload")
        .filter(|value| value.is_object())
        .unwrap_or(payload)
}
