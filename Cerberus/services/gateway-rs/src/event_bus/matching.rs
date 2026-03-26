use crate::gateway_types::OrderEvent;

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

fn payload_for_matching<'a>(payload: &'a serde_json::Value) -> &'a serde_json::Value {
    payload
        .get("payload")
        .filter(|value| value.is_object())
        .unwrap_or(payload)
}
