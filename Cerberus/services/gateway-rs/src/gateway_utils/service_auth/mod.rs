mod cache;
mod fetch;
mod jwt;

use reqwest::RequestBuilder;

use crate::gateway_types::AppState;

use cache::cached_or_fetch_strategy_token;

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

use anyhow::Context;
