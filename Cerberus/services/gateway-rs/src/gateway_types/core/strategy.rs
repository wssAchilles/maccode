use std::sync::Arc;

use tokio::sync::Notify;

#[derive(Clone)]
pub(crate) struct StrategyUpstreamConfig {
    pub(crate) timeout_ms: u64,
    pub(crate) health_timeout_ms: u64,
    pub(crate) max_inflight: usize,
    pub(crate) queue_timeout_ms: u64,
    pub(crate) circuit_enabled: bool,
    pub(crate) circuit_failure_threshold: u64,
    pub(crate) circuit_open_ms: u64,
}

#[derive(Clone, Debug, Default)]
pub(crate) struct StrategyUpstreamCircuitState {
    pub(crate) consecutive_failures: u64,
    pub(crate) opened_at_ms: Option<u64>,
    pub(crate) last_failure_reason: Option<String>,
}

#[derive(Clone, Debug)]
pub(crate) struct CachedJsonPayload {
    pub(crate) payload: serde_json::Value,
    pub(crate) cached_at: u64,
}

#[derive(Clone, Debug)]
pub(crate) struct SummaryInflightEntry {
    pub(crate) waiter: Arc<Notify>,
    pub(crate) started_at_ms: u64,
}
