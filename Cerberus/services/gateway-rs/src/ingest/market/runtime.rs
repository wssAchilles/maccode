use std::{collections::HashMap, env, time::Duration};

use anyhow::Context;
use futures_util::StreamExt;
use redis::{aio::MultiplexedConnection, Script};
use tokio::time::sleep;
use tokio_tungstenite::connect_async;
use tracing::{error, info, warn};
use uuid::Uuid;

use crate::gateway_types::{AppState, MarketEvent, DEFAULT_BINANCE_STREAM_BASE};
use crate::gateway_utils::{current_millis, env_flag, non_empty_env};

use super::decode::parse_market_event;
use super::redis_publish::{connect_redis, publish_market_event};
use super::ws_url::build_binance_market_ws_url;

const DEFAULT_MARKET_PUBLISH_LEADER_LOCK_KEY: &str = "cerberus:market-events:publisher";
const DEFAULT_MARKET_PUBLISH_LEADER_TTL_MS: u64 = 30_000;
const DEFAULT_MARKET_PUBLISH_LEADER_HEARTBEAT_MS: u64 = 10_000;
const DEFAULT_MARKET_PUBLISH_MIN_INTERVAL_MS: u64 = 100;

pub(crate) fn spawn_market_ingest(state: AppState) {
    tokio::spawn(async move {
        loop {
            if let Err(err) = run_ingest_loop(state.clone()).await {
                error!("market ingest failed: {err:#}");
                {
                    let mut metrics = state.metrics.write().await;
                    metrics.last_market_ingest_error = Some(err.to_string());
                }
                sleep(Duration::from_secs(2)).await;
            }
        }
    });
}

async fn run_ingest_loop(state: AppState) -> anyhow::Result<()> {
    let ws_url = env::var("MARKET_WS_URL").unwrap_or_else(|_| {
        build_binance_market_ws_url(
            &state.market_symbols,
            DEFAULT_BINANCE_STREAM_BASE,
            "@bookTicker",
        )
    });
    info!("connecting market stream: {ws_url}");

    let (ws_stream, _) = connect_async(&ws_url)
        .await
        .context("websocket connect failed")?;
    let (_, mut read) = ws_stream.split();
    {
        let mut metrics = state.metrics.write().await;
        metrics.last_market_ingest_error = None;
    }

    let mut publish_controller = MarketPublishController::from_env();

    while let Some(message) = read.next().await {
        let message = message?;
        if !message.is_text() {
            continue;
        }

        let raw = message.to_text()?;
        let Some(event) = parse_market_event(raw) else {
            continue;
        };

        let payload = serde_json::to_string(&event)?;
        publish_controller
            .maybe_publish(&state, &event, payload.as_str())
            .await;

        {
            let mut guard = state.latest_event.write().await;
            *guard = Some(event.clone());
        }
        {
            let mut by_symbol = state.latest_by_symbol.write().await;
            by_symbol.insert(event.symbol.clone(), event.clone());
        }

        {
            let mut metrics = state.metrics.write().await;
            metrics.market_events += 1;
            metrics.last_market_event_at = Some(current_millis());
            metrics.last_market_ingest_error = None;
        }

        let _ = state.market_tx.send(event);
    }

    Ok(())
}

struct MarketPublishController {
    config: MarketPublishOptimizationConfig,
    leader_state: MarketPublishLeaderState,
    leader_conn: Option<MultiplexedConnection>,
    publish_conn: Option<MultiplexedConnection>,
    last_published_by_symbol: HashMap<String, PublishedMarketEventState>,
}

impl MarketPublishController {
    fn from_env() -> Self {
        Self {
            config: MarketPublishOptimizationConfig::from_env(),
            leader_state: MarketPublishLeaderState::new(),
            leader_conn: None,
            publish_conn: None,
            last_published_by_symbol: HashMap::new(),
        }
    }

    async fn maybe_publish(&mut self, state: &AppState, event: &MarketEvent, payload: &str) {
        if state.redis_url.trim().is_empty() {
            return;
        }
        if !state.market_event_stream.enabled && !state.market_event_stream.publish_legacy_pubsub {
            return;
        }
        if !self
            .ensure_publish_permission(state.redis_url.as_str())
            .await
        {
            return;
        }

        let now_ms = current_millis();
        if !should_publish_market_event(
            &self.config,
            self.last_published_by_symbol.get(event.symbol.as_str()),
            event,
            now_ms,
        ) {
            return;
        }

        let published = publish_market_event(state, &mut self.publish_conn, event, payload).await;
        if published {
            self.record_published_event(event, now_ms);
        }
    }

    async fn ensure_publish_permission(&mut self, redis_url: &str) -> bool {
        if !self.config.single_writer_enabled {
            return self.ensure_publish_connection(redis_url).await;
        }

        let now_ms = current_millis();
        if self.leader_state.lock_held
            && now_ms.saturating_sub(self.leader_state.last_lock_renewed_at_ms)
                >= self.config.leader_heartbeat_ms
        {
            if self.try_renew_leader_lock().await {
                self.leader_state.last_lock_renewed_at_ms = now_ms;
            } else {
                self.mark_leadership_lost("market publish leadership renewal failed");
            }
        }

        if self.leader_state.lock_held {
            return self.ensure_publish_connection(redis_url).await;
        }

        if now_ms.saturating_sub(self.leader_state.last_lock_attempt_at_ms)
            < self.config.leader_heartbeat_ms
        {
            return false;
        }
        self.leader_state.last_lock_attempt_at_ms = now_ms;

        if !self.try_acquire_leader_lock(redis_url).await {
            return false;
        }

        self.leader_state.lock_held = true;
        self.leader_state.last_lock_renewed_at_ms = now_ms;
        info!(
            "market publish leadership acquired key={}",
            self.config.leader_lock_key
        );
        self.ensure_publish_connection(redis_url).await
    }

    async fn ensure_publish_connection(&mut self, redis_url: &str) -> bool {
        if self.publish_conn.is_none() {
            self.publish_conn = connect_redis(redis_url).await;
        }
        self.publish_conn.is_some()
    }

    async fn try_acquire_leader_lock(&mut self, redis_url: &str) -> bool {
        if self.leader_conn.is_none() {
            self.leader_conn = connect_redis(redis_url).await;
        }
        let Some(conn) = self.leader_conn.as_mut() else {
            return false;
        };

        let ttl_ms = self.config.leader_ttl_ms.max(1);
        let response = redis::cmd("SET")
            .arg(&self.config.leader_lock_key)
            .arg(self.leader_state.lock_token.as_str())
            .arg("NX")
            .arg("PX")
            .arg(ttl_ms)
            .query_async::<Option<String>>(conn)
            .await;
        match response {
            Ok(result) => result.as_deref() == Some("OK"),
            Err(err) => {
                warn!("market publish leader lock acquisition failed: {err}");
                self.leader_conn = None;
                false
            }
        }
    }

    async fn try_renew_leader_lock(&mut self) -> bool {
        let Some(conn) = self.leader_conn.as_mut() else {
            return false;
        };

        let ttl_ms = self.config.leader_ttl_ms.max(1);
        let script = Script::new(
            r#"
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("pexpire", KEYS[1], ARGV[2])
                end
                return 0
            "#,
        );
        let renewal: redis::RedisResult<i32> = script
            .key(&self.config.leader_lock_key)
            .arg(self.leader_state.lock_token.as_str())
            .arg(ttl_ms)
            .invoke_async(conn)
            .await;
        match renewal {
            Ok(result) => result == 1,
            Err(err) => {
                warn!("market publish leader lock renewal failed: {err}");
                self.leader_conn = None;
                false
            }
        }
    }

    fn mark_leadership_lost(&mut self, reason: &str) {
        if self.leader_state.lock_held {
            info!(
                "market publish leadership released key={} reason={reason}",
                self.config.leader_lock_key
            );
        }
        self.leader_state.lock_held = false;
        self.publish_conn = None;
    }

    fn record_published_event(&mut self, event: &MarketEvent, now_ms: u64) {
        self.last_published_by_symbol.insert(
            event.symbol.clone(),
            PublishedMarketEventState {
                bid_price: event.bid_price.clone(),
                ask_price: event.ask_price.clone(),
                published_at_ms: now_ms,
            },
        );
    }
}

#[derive(Clone, Debug)]
struct MarketPublishOptimizationConfig {
    single_writer_enabled: bool,
    leader_lock_key: String,
    leader_ttl_ms: u64,
    leader_heartbeat_ms: u64,
    min_publish_interval_ms: u64,
    publish_on_price_change_only: bool,
}

impl MarketPublishOptimizationConfig {
    fn from_env() -> Self {
        let leader_ttl_ms = parse_env_u64_value("REDIS_MARKET_EVENTS_LEADER_TTL_MS")
            .filter(|value| *value > 0)
            .unwrap_or(DEFAULT_MARKET_PUBLISH_LEADER_TTL_MS);
        let leader_heartbeat_ms = parse_env_u64_value("REDIS_MARKET_EVENTS_LEADER_HEARTBEAT_MS")
            .filter(|value| *value > 0)
            .unwrap_or(DEFAULT_MARKET_PUBLISH_LEADER_HEARTBEAT_MS)
            .min(leader_ttl_ms);
        Self {
            single_writer_enabled: env_flag("REDIS_MARKET_EVENTS_SINGLE_WRITER_ENABLED", true),
            leader_lock_key: non_empty_env("REDIS_MARKET_EVENTS_LEADER_LOCK_KEY")
                .unwrap_or_else(|| DEFAULT_MARKET_PUBLISH_LEADER_LOCK_KEY.to_string()),
            leader_ttl_ms,
            leader_heartbeat_ms,
            min_publish_interval_ms: parse_env_u64_value(
                "REDIS_MARKET_EVENTS_MIN_PUBLISH_INTERVAL_MS",
            )
            .unwrap_or(DEFAULT_MARKET_PUBLISH_MIN_INTERVAL_MS),
            publish_on_price_change_only: env_flag(
                "REDIS_MARKET_EVENTS_PUBLISH_ON_PRICE_CHANGE_ONLY",
                true,
            ),
        }
    }
}

struct MarketPublishLeaderState {
    lock_token: String,
    lock_held: bool,
    last_lock_attempt_at_ms: u64,
    last_lock_renewed_at_ms: u64,
}

impl MarketPublishLeaderState {
    fn new() -> Self {
        Self {
            lock_token: format!("gateway-market-publisher-{}", Uuid::new_v4()),
            lock_held: false,
            last_lock_attempt_at_ms: 0,
            last_lock_renewed_at_ms: 0,
        }
    }
}

struct PublishedMarketEventState {
    bid_price: String,
    ask_price: String,
    published_at_ms: u64,
}

fn should_publish_market_event(
    config: &MarketPublishOptimizationConfig,
    previous: Option<&PublishedMarketEventState>,
    event: &MarketEvent,
    now_ms: u64,
) -> bool {
    let Some(previous) = previous else {
        return true;
    };

    let price_changed =
        previous.bid_price != event.bid_price || previous.ask_price != event.ask_price;
    if config.publish_on_price_change_only && !price_changed {
        return false;
    }

    now_ms.saturating_sub(previous.published_at_ms) >= config.min_publish_interval_ms
}

fn parse_env_u64_value(key: &str) -> Option<u64> {
    env::var(key).ok()?.trim().parse::<u64>().ok()
}

#[cfg(test)]
mod tests {
    use crate::gateway_types::MarketEvent;

    use super::{
        should_publish_market_event, MarketPublishOptimizationConfig, PublishedMarketEventState,
    };

    fn market_event(symbol: &str, bid_price: &str, ask_price: &str) -> MarketEvent {
        MarketEvent {
            symbol: symbol.to_string(),
            bid_price: bid_price.to_string(),
            ask_price: ask_price.to_string(),
            event_time: 0,
        }
    }

    fn publish_config(min_publish_interval_ms: u64) -> MarketPublishOptimizationConfig {
        MarketPublishOptimizationConfig {
            single_writer_enabled: true,
            leader_lock_key: "cerberus:test".to_string(),
            leader_ttl_ms: 30_000,
            leader_heartbeat_ms: 10_000,
            min_publish_interval_ms,
            publish_on_price_change_only: true,
        }
    }

    #[test]
    fn market_publish_drops_unchanged_quotes() {
        let config = publish_config(100);
        let previous = PublishedMarketEventState {
            bid_price: "100.0".to_string(),
            ask_price: "101.0".to_string(),
            published_at_ms: 1_000,
        };
        assert!(!should_publish_market_event(
            &config,
            Some(&previous),
            &market_event("BTCUSDT", "100.0", "101.0"),
            2_000,
        ));
    }

    #[test]
    fn market_publish_throttles_changed_quotes_within_interval() {
        let config = publish_config(250);
        let previous = PublishedMarketEventState {
            bid_price: "100.0".to_string(),
            ask_price: "101.0".to_string(),
            published_at_ms: 1_000,
        };
        assert!(!should_publish_market_event(
            &config,
            Some(&previous),
            &market_event("BTCUSDT", "100.1", "101.1"),
            1_200,
        ));
    }

    #[test]
    fn market_publish_allows_changed_quotes_after_interval() {
        let config = publish_config(250);
        let previous = PublishedMarketEventState {
            bid_price: "100.0".to_string(),
            ask_price: "101.0".to_string(),
            published_at_ms: 1_000,
        };
        assert!(should_publish_market_event(
            &config,
            Some(&previous),
            &market_event("BTCUSDT", "100.1", "101.1"),
            1_251,
        ));
    }
}
