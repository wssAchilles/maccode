use crate::{
    gateway_types::{AppState, AuthenticatedUser, CachedAuthUser},
    gateway_utils::current_millis,
};

const AUTH_CACHE_TTL_MS: u64 = 60_000;
const AUTH_CACHE_MAX_ENTRIES: usize = 1024;

pub(super) async fn auth_cache_lookup(state: &AppState, token: &str) -> Option<AuthenticatedUser> {
    let now = current_millis();
    let cache = state.auth_cache.read().await;
    cache.get(token).and_then(|entry| {
        if entry.expires_at_ms > now {
            Some(entry.user.clone())
        } else {
            None
        }
    })
}

pub(super) async fn auth_cache_store(state: &AppState, token: &str, user: AuthenticatedUser) {
    let now = current_millis();
    let mut cache = state.auth_cache.write().await;
    cache.retain(|_, entry| entry.expires_at_ms > now);
    if cache.len() >= AUTH_CACHE_MAX_ENTRIES {
        cache.clear();
    }
    cache.insert(
        token.to_string(),
        CachedAuthUser {
            user,
            expires_at_ms: now + AUTH_CACHE_TTL_MS,
        },
    );
}
