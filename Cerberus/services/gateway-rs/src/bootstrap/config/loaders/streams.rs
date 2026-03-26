use std::env;

use uuid::Uuid;

use crate::gateway_types::{MarketEventsStreamPublishConfig, OrderEventsStreamConfig};
use crate::gateway_utils::env_flag;

use super::common::{parse_env_u64, parse_env_usize};

pub(crate) fn load_order_event_stream_config() -> OrderEventsStreamConfig {
    OrderEventsStreamConfig {
        enabled: env_flag("REDIS_ORDER_EVENTS_STREAM_ENABLED", true),
        legacy_pubsub_fallback: env_flag("REDIS_ORDER_EVENTS_LEGACY_PUBSUB_FALLBACK", true),
        stream_key: env::var("REDIS_ORDER_EVENTS_STREAM_KEY")
            .unwrap_or_else(|_| "cerberus.order.events".to_string()),
        consumer_group: env::var("REDIS_ORDER_EVENTS_CONSUMER_GROUP")
            .unwrap_or_else(|_| "gateway-orders".to_string()),
        consumer_name: env::var("REDIS_ORDER_EVENTS_CONSUMER_NAME")
            .ok()
            .map(|raw| raw.trim().to_string())
            .filter(|raw| !raw.is_empty())
            .unwrap_or_else(|| format!("gateway-{}", Uuid::new_v4())),
        read_batch_size: parse_env_usize("REDIS_ORDER_EVENTS_READ_BATCH_SIZE")
            .filter(|value| *value > 0)
            .unwrap_or(64),
        read_block_ms: parse_env_usize("REDIS_ORDER_EVENTS_READ_BLOCK_MS")
            .filter(|value| *value > 0)
            .unwrap_or(3_000),
        pending_replay_count: parse_env_usize("REDIS_ORDER_EVENTS_PENDING_REPLAY_COUNT")
            .filter(|value| *value > 0)
            .unwrap_or(128),
        batch_window_ms: parse_env_u64("REDIS_ORDER_EVENTS_BATCH_WINDOW_MS").unwrap_or(100),
        max_retries_before_fallback: parse_env_usize(
            "REDIS_ORDER_EVENTS_MAX_RETRIES_BEFORE_FALLBACK",
        )
        .unwrap_or(6),
        retry_backoff_base_ms: parse_env_u64("REDIS_ORDER_EVENTS_RETRY_BACKOFF_MS")
            .filter(|value| *value > 0)
            .unwrap_or(200),
        retry_backoff_max_ms: parse_env_u64("REDIS_ORDER_EVENTS_RETRY_BACKOFF_MAX_MS")
            .filter(|value| *value > 0)
            .unwrap_or(5_000),
        reclaim_enabled: env_flag("REDIS_ORDER_EVENTS_RECLAIM_ENABLED", true),
        reclaim_interval_ms: parse_env_u64("REDIS_ORDER_EVENTS_RECLAIM_INTERVAL_MS")
            .unwrap_or(5_000),
        reclaim_idle_ms: parse_env_u64("REDIS_ORDER_EVENTS_RECLAIM_IDLE_MS")
            .filter(|value| *value > 0)
            .unwrap_or(30_000),
        reclaim_batch_size: parse_env_usize("REDIS_ORDER_EVENTS_RECLAIM_BATCH_SIZE")
            .filter(|value| *value > 0)
            .unwrap_or(64),
        max_delivery_attempts: parse_env_usize("REDIS_ORDER_EVENTS_MAX_DELIVERY_ATTEMPTS")
            .unwrap_or(8),
        poison_stream_key: env::var("REDIS_ORDER_EVENTS_POISON_STREAM_KEY")
            .ok()
            .map(|raw| raw.trim().to_string())
            .filter(|raw| !raw.is_empty())
            .unwrap_or_else(|| "cerberus.order.events.poison".to_string()),
        poison_stream_maxlen: parse_env_usize("REDIS_ORDER_EVENTS_POISON_STREAM_MAXLEN")
            .filter(|value| *value > 0)
            .unwrap_or(20_000),
        pending_warn_threshold: parse_env_usize("REDIS_ORDER_EVENTS_PENDING_WARN_THRESHOLD")
            .unwrap_or(2_000),
        lag_warn_threshold: parse_env_usize("REDIS_ORDER_EVENTS_LAG_WARN_THRESHOLD")
            .unwrap_or(2_000),
    }
}

pub(crate) fn load_market_event_stream_config() -> MarketEventsStreamPublishConfig {
    MarketEventsStreamPublishConfig {
        enabled: env_flag("REDIS_MARKET_EVENTS_STREAM_ENABLED", true),
        stream_key: env::var("REDIS_MARKET_EVENTS_STREAM_KEY")
            .unwrap_or_else(|_| "cerberus.market.events".to_string()),
        max_len: parse_env_usize("REDIS_MARKET_EVENTS_STREAM_MAXLEN")
            .filter(|value| *value > 0)
            .unwrap_or(50_000),
        publish_legacy_pubsub: env_flag("REDIS_MARKET_EVENTS_PUBLISH_LEGACY_PUBSUB", true),
        schema_version: env::var("CERBERUS_EVENT_SCHEMA_VERSION")
            .ok()
            .map(|raw| raw.trim().to_string())
            .filter(|raw| !raw.is_empty())
            .unwrap_or_else(|| "v1".to_string()),
    }
}
