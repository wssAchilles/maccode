use crate::gateway_types::{AppState, CachedJsonPayload};
use crate::gateway_utils::current_millis;

pub(super) async fn read_summary_cache(
    state: &AppState,
    cache_key: &str,
) -> Option<serde_json::Value> {
    let now = current_millis();
    let ttl = state.strategy_summary_cache_ttl_ms;
    let cache = state.strategy_summary_cache.read().await;
    cache.get(cache_key).and_then(|entry| {
        if now.saturating_sub(entry.cached_at) <= ttl {
            Some(entry.payload.clone())
        } else {
            None
        }
    })
}

pub(super) async fn write_summary_cache(
    state: &AppState,
    cache_key: String,
    payload: serde_json::Value,
) {
    let mut cache = state.strategy_summary_cache.write().await;
    cache.insert(
        cache_key,
        CachedJsonPayload {
            payload,
            cached_at: current_millis(),
        },
    );
    if cache.len() > 256 {
        let keys = cache.keys().take(64).cloned().collect::<Vec<_>>();
        for key in keys {
            cache.remove(&key);
        }
    }
}
