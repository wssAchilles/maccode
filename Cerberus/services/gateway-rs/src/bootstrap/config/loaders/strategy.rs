use std::env;

use crate::gateway_types::{InternalServiceAuthConfig, StrategyUpstreamConfig};
use crate::gateway_utils::{env_flag, non_empty_env};

use super::common::{parse_env_u64, parse_env_usize};

pub(crate) fn load_strategy_internal_auth_config(
    strategy_base_url: Option<&String>,
) -> InternalServiceAuthConfig {
    InternalServiceAuthConfig {
        enabled: env_flag("STRATEGY_INTERNAL_AUTH_ENABLED", false),
        audience: non_empty_env("STRATEGY_INTERNAL_AUTH_AUDIENCE")
            .or_else(|| strategy_base_url.cloned()),
        metadata_identity_url: env::var("GCP_METADATA_IDENTITY_URL").unwrap_or_else(|_| {
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity".to_string()
        }),
        token_cache_ttl_seconds: parse_env_u64("STRATEGY_INTERNAL_AUTH_TOKEN_TTL_SECONDS")
            .filter(|value| *value > 0)
            .unwrap_or(300),
    }
}

pub(crate) fn load_strategy_upstream_config() -> StrategyUpstreamConfig {
    StrategyUpstreamConfig {
        timeout_ms: parse_env_u64("STRATEGY_UPSTREAM_TIMEOUT_MS")
            .filter(|value| *value > 0)
            .unwrap_or(1_800),
        health_timeout_ms: parse_env_u64("STRATEGY_UPSTREAM_HEALTH_TIMEOUT_MS")
            .filter(|value| *value > 0)
            .unwrap_or(1_500),
        max_inflight: parse_env_usize("STRATEGY_UPSTREAM_MAX_INFLIGHT")
            .filter(|value| *value > 0)
            .unwrap_or(64),
        queue_timeout_ms: parse_env_u64("STRATEGY_UPSTREAM_QUEUE_TIMEOUT_MS")
            .filter(|value| *value > 0)
            .unwrap_or(250),
        circuit_enabled: env_flag("STRATEGY_UPSTREAM_CIRCUIT_ENABLED", true),
        circuit_failure_threshold: parse_env_u64("STRATEGY_UPSTREAM_CIRCUIT_FAILURE_THRESHOLD")
            .filter(|value| *value > 0)
            .unwrap_or(6),
        circuit_open_ms: parse_env_u64("STRATEGY_UPSTREAM_CIRCUIT_OPEN_MS")
            .filter(|value| *value > 0)
            .unwrap_or(15_000),
    }
}
