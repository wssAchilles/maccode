use crate::gateway_types::{AppState, CachedInternalServiceToken};

use super::fetch::fetch_strategy_identity_token;
use super::jwt::{current_millis_local, derive_token_cache_expiry};

pub(super) async fn cached_or_fetch_strategy_token(
    state: &AppState,
    audience: &str,
) -> anyhow::Result<String> {
    let now_ms = current_millis_local();
    {
        let cache = state.strategy_internal_token_cache.read().await;
        if let Some(cached) = cache.as_ref() {
            if cached.expires_at_ms > now_ms.saturating_add(5_000) {
                return Ok(cached.token.clone());
            }
        }
    }

    let token = fetch_strategy_identity_token(state, audience).await?;
    let cache_ttl_ms = state
        .strategy_internal_auth
        .token_cache_ttl_seconds
        .max(30)
        .saturating_mul(1_000);
    let expires_at_ms = derive_token_cache_expiry(&token, now_ms, cache_ttl_ms);
    let cached = CachedInternalServiceToken {
        token: token.clone(),
        expires_at_ms,
    };
    let mut cache = state.strategy_internal_token_cache.write().await;
    *cache = Some(cached);
    Ok(token)
}
