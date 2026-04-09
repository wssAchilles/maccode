use std::{
    collections::HashMap,
    sync::{
        Arc,
        atomic::{AtomicU64, Ordering},
    },
    time::{SystemTime, UNIX_EPOCH},
};

use reqwest::Error as ReqwestError;
use serde::{Deserialize, Serialize};
use tokio::sync::Mutex;

pub const PYTHON_WORKER_KEY: &str = "python_worker";
pub const HEAVY_WORKER_KEY: &str = "heavy_worker";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkerConfig {
    pub worker_key: String,
    pub base_url: Option<String>,
    pub required: bool,
}

impl WorkerConfig {
    pub fn required(worker_key: impl Into<String>, base_url: Option<String>) -> Self {
        Self {
            worker_key: worker_key.into(),
            base_url,
            required: true,
        }
    }

    pub fn optional(worker_key: impl Into<String>, base_url: Option<String>) -> Self {
        Self {
            worker_key: worker_key.into(),
            base_url,
            required: false,
        }
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum UpstreamReachability {
    Unconfigured,
    Unknown,
    Reachable,
    Degraded,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum UpstreamFailureKind {
    ConnectTimeout,
    ReadTimeout,
    BadStatus,
    DecodeError,
    SseProxyError,
    RequestError,
}

impl UpstreamFailureKind {
    pub fn error_code(self) -> &'static str {
        match self {
            Self::ConnectTimeout => "UPSTREAM_CONNECT_TIMEOUT",
            Self::ReadTimeout => "UPSTREAM_READ_TIMEOUT",
            Self::BadStatus => "UPSTREAM_BAD_STATUS",
            Self::DecodeError => "UPSTREAM_DECODE_ERROR",
            Self::SseProxyError => "UPSTREAM_SSE_PROXY_ERROR",
            Self::RequestError => "UPSTREAM_REQUEST_ERROR",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct UpstreamFailureRecord {
    pub kind: UpstreamFailureKind,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub status_code: Option<u16>,
    pub observed_at_ms: u64,
    pub sequence: u64,
}

impl UpstreamFailureRecord {
    pub fn new(kind: UpstreamFailureKind, message: impl Into<String>) -> Self {
        Self {
            kind,
            message: message.into(),
            status_code: None,
            observed_at_ms: now_ms(),
            sequence: 0,
        }
    }

    pub fn with_status_code(mut self, status_code: u16) -> Self {
        self.status_code = Some(status_code);
        self
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct WorkerHealthSnapshot {
    pub worker_key: String,
    pub configured: bool,
    pub required: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub base_url: Option<String>,
    pub reachability: UpstreamReachability,
    pub degraded: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_successful_contact_at_ms: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_error: Option<UpstreamFailureRecord>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct UpstreamHealthSummary {
    pub upstream_reachability: UpstreamReachability,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_upstream_error: Option<UpstreamFailureRecord>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_successful_contact_at_ms: Option<u64>,
    pub degraded: bool,
    pub degraded_components: Vec<String>,
    pub worker_health: Vec<WorkerHealthSnapshot>,
}

#[derive(Debug, Clone, Default)]
struct WorkerHealthState {
    last_successful_contact_at_ms: Option<u64>,
    last_success_sequence: Option<u64>,
    last_error: Option<UpstreamFailureRecord>,
}

#[derive(Clone, Default)]
pub struct WorkerHealthRegistry {
    states: Arc<Mutex<HashMap<String, WorkerHealthState>>>,
    sequence: Arc<AtomicU64>,
}

impl WorkerHealthRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    pub async fn record_success(&self, worker_key: &str) {
        let sequence = self.next_sequence();
        let mut states = self.states.lock().await;
        let state = states.entry(worker_key.to_string()).or_default();
        state.last_successful_contact_at_ms = Some(now_ms());
        state.last_success_sequence = Some(sequence);
    }

    pub async fn record_failure(&self, worker_key: &str, mut failure: UpstreamFailureRecord) {
        let sequence = self.next_sequence();
        if failure.observed_at_ms == 0 {
            failure.observed_at_ms = now_ms();
        }
        failure.sequence = sequence;

        let mut states = self.states.lock().await;
        let state = states.entry(worker_key.to_string()).or_default();
        state.last_error = Some(failure);
    }

    pub async fn summary(&self, configs: &[WorkerConfig]) -> UpstreamHealthSummary {
        let states = self.states.lock().await;
        let worker_health: Vec<WorkerHealthSnapshot> = configs
            .iter()
            .map(|config| {
                let state = states.get(&config.worker_key);
                build_worker_snapshot(config, state)
            })
            .collect();
        drop(states);

        let degraded_components = worker_health
            .iter()
            .filter(|worker| worker.degraded)
            .map(|worker| worker.worker_key.clone())
            .collect::<Vec<_>>();

        let last_upstream_error = worker_health
            .iter()
            .filter_map(|worker| worker.last_error.clone())
            .max_by_key(|error| error.sequence);

        let last_successful_contact_at_ms = worker_health
            .iter()
            .filter_map(|worker| worker.last_successful_contact_at_ms)
            .max();

        UpstreamHealthSummary {
            upstream_reachability: aggregate_reachability(&worker_health),
            last_upstream_error,
            last_successful_contact_at_ms,
            degraded: !degraded_components.is_empty(),
            degraded_components,
            worker_health,
        }
    }

    fn next_sequence(&self) -> u64 {
        self.sequence.fetch_add(1, Ordering::Relaxed) + 1
    }
}

pub fn classify_reqwest_error(error: &ReqwestError, is_sse: bool) -> UpstreamFailureKind {
    if error.is_timeout() {
        if error.is_connect() {
            return UpstreamFailureKind::ConnectTimeout;
        }
        return UpstreamFailureKind::ReadTimeout;
    }

    if error.is_connect() {
        return UpstreamFailureKind::ConnectTimeout;
    }

    if is_sse {
        return UpstreamFailureKind::SseProxyError;
    }

    UpstreamFailureKind::RequestError
}

fn build_worker_snapshot(
    config: &WorkerConfig,
    state: Option<&WorkerHealthState>,
) -> WorkerHealthSnapshot {
    let configured = config.base_url.is_some();
    let last_successful_contact_at_ms = state.and_then(|state| state.last_successful_contact_at_ms);
    let last_success_sequence = state.and_then(|state| state.last_success_sequence);
    let last_error = state.and_then(|state| state.last_error.clone());

    let reachability = if !configured {
        UpstreamReachability::Unconfigured
    } else if let Some(error) = last_error.as_ref() {
        if last_success_sequence.is_none_or(|sequence| error.sequence > sequence) {
            UpstreamReachability::Degraded
        } else {
            UpstreamReachability::Reachable
        }
    } else if last_success_sequence.is_some() {
        UpstreamReachability::Reachable
    } else {
        UpstreamReachability::Unknown
    };

    let degraded = match reachability {
        UpstreamReachability::Unconfigured => config.required,
        UpstreamReachability::Degraded => true,
        UpstreamReachability::Unknown | UpstreamReachability::Reachable => false,
    };

    WorkerHealthSnapshot {
        worker_key: config.worker_key.clone(),
        configured,
        required: config.required,
        base_url: config.base_url.clone(),
        reachability,
        degraded,
        last_successful_contact_at_ms,
        last_error,
    }
}

fn aggregate_reachability(worker_health: &[WorkerHealthSnapshot]) -> UpstreamReachability {
    let required_workers = worker_health.iter().filter(|worker| worker.required);
    let (has_unconfigured, has_degraded, has_unknown, has_reachable) =
        required_workers.fold((false, false, false, false), |mut state, worker| {
            match worker.reachability {
                UpstreamReachability::Unconfigured => state.0 = true,
                UpstreamReachability::Degraded => state.1 = true,
                UpstreamReachability::Unknown => state.2 = true,
                UpstreamReachability::Reachable => state.3 = true,
            }
            state
        });

    if has_unconfigured {
        UpstreamReachability::Unconfigured
    } else if has_degraded {
        UpstreamReachability::Degraded
    } else if has_unknown {
        UpstreamReachability::Unknown
    } else if has_reachable {
        UpstreamReachability::Reachable
    } else {
        UpstreamReachability::Unknown
    }
}

fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn required_worker_without_configuration_is_unconfigured_and_degraded() {
        let registry = WorkerHealthRegistry::new();

        let summary = registry
            .summary(&[WorkerConfig::required("python_worker", None)])
            .await;

        assert_eq!(
            summary.upstream_reachability,
            UpstreamReachability::Unconfigured
        );
        assert!(summary.degraded);
        assert_eq!(
            summary.degraded_components,
            vec!["python_worker".to_string()]
        );

        let worker = summary
            .worker_health
            .iter()
            .find(|worker| worker.worker_key == "python_worker")
            .expect("python worker snapshot should be present");
        assert_eq!(worker.reachability, UpstreamReachability::Unconfigured);
    }

    #[tokio::test]
    async fn successful_contact_marks_required_worker_reachable() {
        let registry = WorkerHealthRegistry::new();
        registry.record_success("python_worker").await;

        let summary = registry
            .summary(&[WorkerConfig::required(
                "python_worker",
                Some("https://python-worker.internal".to_string()),
            )])
            .await;

        assert_eq!(
            summary.upstream_reachability,
            UpstreamReachability::Reachable
        );
        assert!(!summary.degraded);
        assert!(summary.last_successful_contact_at_ms.is_some());

        let worker = summary
            .worker_health
            .iter()
            .find(|worker| worker.worker_key == "python_worker")
            .expect("python worker snapshot should be present");
        assert_eq!(worker.reachability, UpstreamReachability::Reachable);
        assert!(worker.last_successful_contact_at_ms.is_some());
    }

    #[tokio::test]
    async fn later_failure_marks_required_worker_degraded_and_preserves_failure_kind() {
        let registry = WorkerHealthRegistry::new();
        registry.record_success("python_worker").await;
        registry
            .record_failure(
                "python_worker",
                UpstreamFailureRecord::new(
                    UpstreamFailureKind::ReadTimeout,
                    "The read operation timed out",
                ),
            )
            .await;

        let summary = registry
            .summary(&[WorkerConfig::required(
                "python_worker",
                Some("https://python-worker.internal".to_string()),
            )])
            .await;

        assert_eq!(
            summary.upstream_reachability,
            UpstreamReachability::Degraded
        );
        assert!(summary.degraded);
        assert_eq!(
            summary.degraded_components,
            vec!["python_worker".to_string()]
        );

        let error = summary
            .last_upstream_error
            .expect("summary should expose the latest upstream error");
        assert_eq!(error.kind, UpstreamFailureKind::ReadTimeout);
        assert!(error.observed_at_ms > 0);
    }

    #[tokio::test]
    async fn optional_unconfigured_worker_does_not_degrade_healthy_required_worker() {
        let registry = WorkerHealthRegistry::new();
        registry.record_success("python_worker").await;

        let summary = registry
            .summary(&[
                WorkerConfig::required(
                    "python_worker",
                    Some("https://python-worker.internal".to_string()),
                ),
                WorkerConfig::optional("heavy_worker", None),
            ])
            .await;

        assert_eq!(
            summary.upstream_reachability,
            UpstreamReachability::Reachable
        );
        assert!(!summary.degraded);
        assert!(summary.degraded_components.is_empty());

        let heavy_worker = summary
            .worker_health
            .iter()
            .find(|worker| worker.worker_key == "heavy_worker")
            .expect("heavy worker snapshot should be present");
        assert_eq!(
            heavy_worker.reachability,
            UpstreamReachability::Unconfigured
        );
        assert!(!heavy_worker.degraded);
    }
}
