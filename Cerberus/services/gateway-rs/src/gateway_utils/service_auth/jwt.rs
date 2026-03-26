use std::time::{SystemTime, UNIX_EPOCH};

use base64::Engine;

const TOKEN_EXPIRY_SKEW_MS: u64 = 10_000;

pub(super) fn current_millis_local() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|value| value.as_millis() as u64)
        .unwrap_or(0)
}

pub(super) fn derive_token_cache_expiry(token: &str, now_ms: u64, configured_ttl_ms: u64) -> u64 {
    let configured_expiry = now_ms.saturating_add(configured_ttl_ms.max(1_000));
    let Some(jwt_exp_ms) = parse_jwt_exp_millis(token) else {
        return configured_expiry;
    };
    let bounded_jwt_expiry = jwt_exp_ms.saturating_sub(TOKEN_EXPIRY_SKEW_MS);
    if bounded_jwt_expiry <= now_ms {
        return now_ms.saturating_add(30_000);
    }
    configured_expiry.min(bounded_jwt_expiry)
}

fn parse_jwt_exp_millis(token: &str) -> Option<u64> {
    let mut parts = token.split('.');
    let _header = parts.next()?;
    let payload = parts.next()?;
    let decoded = decode_jwt_segment(payload)?;
    let payload_json: serde_json::Value = serde_json::from_slice(&decoded).ok()?;
    let exp_seconds = payload_json.get("exp")?.as_u64()?;
    Some(exp_seconds.saturating_mul(1_000))
}

fn decode_jwt_segment(segment: &str) -> Option<Vec<u8>> {
    base64::engine::general_purpose::URL_SAFE_NO_PAD
        .decode(segment.as_bytes())
        .or_else(|_| base64::engine::general_purpose::URL_SAFE.decode(segment.as_bytes()))
        .ok()
}
