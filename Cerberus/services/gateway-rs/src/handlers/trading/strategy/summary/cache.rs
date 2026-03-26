use std::{sync::Arc, time::Duration};

use tokio::{sync::Notify, time::timeout};

use crate::gateway_types::{AppState, CachedJsonPayload, SummaryInflightEntry};
use crate::gateway_utils::current_millis;

pub(super) enum SummaryInflightRole {
    Leader(Arc<Notify>),
    Follower(Arc<Notify>),
}

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

pub(super) async fn begin_summary_inflight(
    state: &AppState,
    cache_key: &str,
) -> SummaryInflightRole {
    let mut inflight = state.strategy_summary_inflight.write().await;
    let stale_waiter = inflight.get(cache_key).and_then(|entry| {
        if is_stale_inflight_entry(state, entry.started_at_ms) {
            Some(entry.waiter.clone())
        } else {
            None
        }
    });
    if let Some(waiter) = stale_waiter {
        inflight.remove(cache_key);
        waiter.notify_waiters();
    } else if let Some(entry) = inflight.get(cache_key) {
        return SummaryInflightRole::Follower(entry.waiter.clone());
    }

    let waiter = Arc::new(Notify::new());
    inflight.insert(
        cache_key.to_string(),
        SummaryInflightEntry {
            waiter: waiter.clone(),
            started_at_ms: current_millis(),
        },
    );
    SummaryInflightRole::Leader(waiter)
}

pub(super) async fn finish_summary_inflight(
    state: &AppState,
    cache_key: &str,
    waiter: &Arc<Notify>,
) {
    {
        let mut inflight = state.strategy_summary_inflight.write().await;
        if let Some(current) = inflight.get(cache_key) {
            if Arc::ptr_eq(&current.waiter, waiter) {
                inflight.remove(cache_key);
            }
        }
    }
    waiter.notify_waiters();
}

fn is_stale_inflight_entry(state: &AppState, started_at_ms: u64) -> bool {
    current_millis().saturating_sub(started_at_ms) >= stale_inflight_ttl_ms(state)
}

fn stale_inflight_ttl_ms(state: &AppState) -> u64 {
    state
        .strategy_upstream
        .timeout_ms
        .saturating_add(state.strategy_summary_batch_window_ms)
        .saturating_add(1_000)
        .max(1_000)
}

pub(super) async fn wait_for_summary_inflight(state: &AppState, waiter: Arc<Notify>) {
    let wait_ms = state
        .strategy_upstream
        .timeout_ms
        .saturating_add(state.strategy_summary_batch_window_ms)
        .max(50);
    let _ = timeout(Duration::from_millis(wait_ms), waiter.notified()).await;
}

pub(super) async fn write_summary_cache(
    state: &AppState,
    cache_key: String,
    payload: serde_json::Value,
) {
    let mut cache = state.strategy_summary_cache.write().await;
    let now = current_millis();
    let ttl = state.strategy_summary_cache_ttl_ms;
    cache.retain(|_, entry| now.saturating_sub(entry.cached_at) <= ttl);
    cache.insert(
        cache_key,
        CachedJsonPayload {
            payload,
            cached_at: now,
        },
    );
    if cache.len() > 256 {
        let keys = cache.keys().take(64).cloned().collect::<Vec<_>>();
        for key in keys {
            cache.remove(&key);
        }
    }
}
