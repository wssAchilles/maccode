use redis::streams::StreamId;

pub(super) fn decode_stream_payload(entry: &StreamId) -> Option<serde_json::Value> {
    let raw = entry
        .get::<String>("data")
        .or_else(|| entry.get::<String>("payload"))
        .or_else(|| entry.get::<String>("json"))?;
    serde_json::from_str::<serde_json::Value>(&raw).ok()
}

pub(super) fn stringify_stream_entry(entry: &StreamId) -> String {
    let mut pairs = Vec::<String>::new();
    for (field, value) in &entry.map {
        let value_text = redis::from_redis_value::<String>(value).unwrap_or_default();
        pairs.push(format!("{field}={value_text}"));
    }
    pairs.join(",")
}

pub(super) fn extract_stream_channel(payload: &serde_json::Value, fallback: &str) -> String {
    payload
        .get("channel")
        .or_else(|| payload.get("event_type"))
        .and_then(|value| value.as_str())
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .unwrap_or(fallback)
        .to_string()
}
