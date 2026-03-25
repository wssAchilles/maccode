use std::time::{Duration, SystemTime, UNIX_EPOCH};

use anyhow::{bail, Context};
use reqwest::RequestBuilder;

use crate::gateway_types::{AppState, CachedInternalServiceToken};

const METADATA_FLAVOR_HEADER: &str = "Metadata-Flavor";
const METADATA_FLAVOR_VALUE: &str = "Google";

pub(crate) async fn with_strategy_internal_auth(
    state: &AppState,
    request: RequestBuilder,
) -> anyhow::Result<RequestBuilder> {
    if !state.strategy_internal_auth.enabled {
        return Ok(request);
    }
    let audience = state
        .strategy_internal_auth
        .audience
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .context("strategy internal auth enabled but audience is empty")?;
    let token = cached_or_fetch_strategy_token(state, audience).await?;
    Ok(request.bearer_auth(token))
}

async fn cached_or_fetch_strategy_token(
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
    let ttl_seconds = state.strategy_internal_auth.token_cache_ttl_seconds.max(30);
    let cached = CachedInternalServiceToken {
        token: token.clone(),
        expires_at_ms: now_ms.saturating_add(ttl_seconds.saturating_mul(1_000)),
    };
    let mut cache = state.strategy_internal_token_cache.write().await;
    *cache = Some(cached);
    Ok(token)
}

async fn fetch_strategy_identity_token(state: &AppState, audience: &str) -> anyhow::Result<String> {
    let response = state
        .http_client
        .get(state.strategy_internal_auth.metadata_identity_url.as_str())
        .query(&[("audience", audience), ("format", "full")])
        .header(METADATA_FLAVOR_HEADER, METADATA_FLAVOR_VALUE)
        .timeout(Duration::from_millis(1_500))
        .send()
        .await
        .context("metadata identity request failed")?;

    let status = response.status();
    let raw_body = response
        .text()
        .await
        .context("metadata identity response read failed")?;
    if !status.is_success() {
        let trimmed = raw_body.trim();
        let body = if trimmed.is_empty() {
            "<empty>"
        } else {
            trimmed
        };
        bail!(
            "metadata identity request status={} body={}",
            status.as_u16(),
            body
        );
    }
    let token = raw_body.trim();
    if token.is_empty() {
        bail!("metadata identity returned empty token");
    }
    Ok(token.to_string())
}

fn current_millis_local() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|value| value.as_millis() as u64)
        .unwrap_or(0)
}
