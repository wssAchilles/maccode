use anyhow::bail;
use tracing::warn;

use crate::gateway_types::AppState;

pub(crate) fn validate_runtime_policies(state: &AppState) -> anyhow::Result<()> {
    let is_production = state
        .jwt_auth
        .environment
        .eq_ignore_ascii_case("production");

    if state.strategy_internal_auth.enabled && state.strategy_internal_auth.audience.is_none() {
        let msg = "STRATEGY_INTERNAL_AUTH_ENABLED=true but STRATEGY_INTERNAL_AUTH_AUDIENCE/STRATEGY_BASE_URL is missing";
        if is_production {
            bail!("{msg}");
        }
        warn!("{msg}; upstream strategy calls will fail");
    }

    if state.jwt_auth.effective_required() && state.jwt_auth.hs256_secret.is_none() {
        let msg = "JWT auth is enabled/required but JWT_HS256_SECRET is missing";
        if is_production {
            bail!("{msg}");
        }
        warn!("{msg}; protected routes will reject requests");
    }

    if state.firebase_auth.required && state.firebase_auth.web_api_key.is_none() {
        bail!("FIREBASE_AUTH_REQUIRED=true but FIREBASE_WEB_API_KEY is missing");
    }

    if state.firebase_auth.required && state.firebase_auth.project_id.is_none() {
        warn!(
            "FIREBASE_AUTH_REQUIRED=true but FIREBASE_PROJECT_ID is empty; token audience checks rely on web API key only"
        );
    }

    if is_production && state.redis_url.trim().is_empty() {
        bail!("REDIS_URL cannot be empty in production");
    }
    if is_production
        && state.order_event_stream.enabled
        && state.order_event_stream.legacy_pubsub_fallback
    {
        bail!("REDIS_ORDER_EVENTS_LEGACY_PUBSUB_FALLBACK must be false when APP_ENV=production");
    }
    if is_production
        && state.market_event_stream.enabled
        && state.market_event_stream.publish_legacy_pubsub
    {
        bail!("REDIS_MARKET_EVENTS_PUBLISH_LEGACY_PUBSUB must be false when APP_ENV=production");
    }

    Ok(())
}
