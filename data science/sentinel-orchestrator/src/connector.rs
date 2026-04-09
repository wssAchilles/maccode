use serde::{Deserialize, Serialize};

use crate::upstream::{
    UpstreamHealthSummary, UpstreamReachability, WorkerConfig, WorkerHealthSnapshot,
};

const PYTHON_WORKER_CAPABILITIES: &[&str] = &[
    "operations.fetch",
    "operations.dispatch",
    "operations.control",
    "operations.stream",
    "control_tasks.projection",
    "compute.telemetry",
];
const HEAVY_WORKER_CAPABILITIES: &[&str] = &["operations.dispatch.heavy"];

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ConnectorState {
    Unconfigured,
    Unknown,
    Healthy,
    Degraded,
    Failed,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ConnectorHealthcheck {
    pub connector_name: String,
    pub state: ConnectorState,
    pub required: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub base_url: Option<String>,
    #[serde(default)]
    pub available_capabilities: Vec<String>,
    #[serde(default)]
    pub unavailable_capabilities: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ConnectorDegradedMode {
    #[serde(default)]
    pub available_connectors: Vec<String>,
    #[serde(default)]
    pub degraded_connectors: Vec<String>,
    #[serde(default)]
    pub available_capabilities: Vec<String>,
    #[serde(default)]
    pub unavailable_capabilities: Vec<String>,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ConnectorLifecycleSnapshot {
    #[serde(default)]
    pub connectors: Vec<ConnectorHealthcheck>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub degraded_mode: Option<ConnectorDegradedMode>,
}

pub fn build_connector_lifecycle(
    configs: &[WorkerConfig],
    summary: &UpstreamHealthSummary,
) -> ConnectorLifecycleSnapshot {
    let connectors: Vec<ConnectorHealthcheck> = summary
        .worker_health
        .iter()
        .map(|worker| connector_from_worker(worker, configs))
        .collect();

    let available_connectors: Vec<String> = connectors
        .iter()
        .filter(|connector| {
            matches!(
                connector.state,
                ConnectorState::Healthy | ConnectorState::Unknown
            )
        })
        .map(|connector| connector.connector_name.clone())
        .collect();
    let degraded_connectors: Vec<String> = connectors
        .iter()
        .filter(|connector| {
            matches!(
                connector.state,
                ConnectorState::Unconfigured | ConnectorState::Degraded | ConnectorState::Failed
            )
        })
        .map(|connector| connector.connector_name.clone())
        .collect();

    let degraded_mode = if degraded_connectors.is_empty() {
        None
    } else {
        let available_capabilities = connectors
            .iter()
            .filter(|connector| available_connectors.contains(&connector.connector_name))
            .flat_map(|connector| connector.available_capabilities.clone())
            .collect::<Vec<_>>();
        let unavailable_capabilities = connectors
            .iter()
            .filter(|connector| degraded_connectors.contains(&connector.connector_name))
            .flat_map(|connector| {
                if connector.unavailable_capabilities.is_empty() {
                    connector.available_capabilities.clone()
                } else {
                    connector.unavailable_capabilities.clone()
                }
            })
            .collect::<Vec<_>>();
        Some(ConnectorDegradedMode {
            available_connectors,
            degraded_connectors: degraded_connectors.clone(),
            available_capabilities,
            unavailable_capabilities,
            reason: degraded_reason(summary.upstream_reachability, &degraded_connectors),
        })
    };

    ConnectorLifecycleSnapshot {
        connectors,
        degraded_mode,
    }
}

fn connector_from_worker(
    worker: &WorkerHealthSnapshot,
    configs: &[WorkerConfig],
) -> ConnectorHealthcheck {
    let config = configs
        .iter()
        .find(|config| config.worker_key == worker.worker_key);
    let capabilities = connector_capabilities(&worker.worker_key)
        .iter()
        .map(|capability| capability.to_string())
        .collect::<Vec<_>>();
    let state = match worker.reachability {
        UpstreamReachability::Unconfigured => ConnectorState::Unconfigured,
        UpstreamReachability::Unknown => ConnectorState::Unknown,
        UpstreamReachability::Reachable => ConnectorState::Healthy,
        UpstreamReachability::Degraded => {
            if config.is_some_and(|entry| entry.required) {
                ConnectorState::Failed
            } else {
                ConnectorState::Degraded
            }
        }
    };
    let (available_capabilities, unavailable_capabilities) = match state {
        ConnectorState::Healthy | ConnectorState::Unknown => (capabilities, Vec::new()),
        ConnectorState::Unconfigured | ConnectorState::Degraded | ConnectorState::Failed => {
            (Vec::new(), capabilities)
        }
    };

    ConnectorHealthcheck {
        connector_name: worker.worker_key.clone(),
        state,
        required: worker.required,
        base_url: worker.base_url.clone(),
        available_capabilities,
        unavailable_capabilities,
        last_error: worker
            .last_error
            .as_ref()
            .map(|error| error.message.clone()),
    }
}

fn connector_capabilities(worker_key: &str) -> &'static [&'static str] {
    match worker_key {
        "heavy_worker" => HEAVY_WORKER_CAPABILITIES,
        _ => PYTHON_WORKER_CAPABILITIES,
    }
}

fn degraded_reason(reachability: UpstreamReachability, degraded_connectors: &[String]) -> String {
    let prefix = match reachability {
        UpstreamReachability::Reachable => "connectors degraded",
        UpstreamReachability::Unknown => "connector health pending",
        UpstreamReachability::Degraded => "connectors degraded",
        UpstreamReachability::Unconfigured => "required connectors unconfigured",
    };
    format!("{prefix}: {}", degraded_connectors.join(", "))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::upstream::{UpstreamFailureKind, UpstreamFailureRecord};

    #[test]
    fn connector_lifecycle_marks_required_degraded_connector_as_failed() {
        let configs = vec![WorkerConfig::required(
            "python_worker",
            Some("https://python.internal".to_string()),
        )];
        let summary = UpstreamHealthSummary {
            upstream_reachability: UpstreamReachability::Degraded,
            last_upstream_error: Some(UpstreamFailureRecord::new(
                UpstreamFailureKind::ReadTimeout,
                "The read operation timed out",
            )),
            last_successful_contact_at_ms: None,
            degraded: true,
            degraded_components: vec!["python_worker".to_string()],
            worker_health: vec![WorkerHealthSnapshot {
                worker_key: "python_worker".to_string(),
                configured: true,
                required: true,
                base_url: Some("https://python.internal".to_string()),
                reachability: UpstreamReachability::Degraded,
                degraded: true,
                last_successful_contact_at_ms: None,
                last_error: Some(UpstreamFailureRecord::new(
                    UpstreamFailureKind::ReadTimeout,
                    "The read operation timed out",
                )),
            }],
        };

        let lifecycle = build_connector_lifecycle(&configs, &summary);
        assert_eq!(lifecycle.connectors.len(), 1);
        assert_eq!(lifecycle.connectors[0].state, ConnectorState::Failed);
        let degraded_mode = lifecycle.degraded_mode.expect("degraded mode");
        assert_eq!(
            degraded_mode.degraded_connectors,
            vec!["python_worker".to_string()]
        );
        assert!(
            degraded_mode
                .unavailable_capabilities
                .contains(&"operations.dispatch".to_string())
        );
    }

    #[test]
    fn connector_lifecycle_keeps_healthy_connector_capabilities_available() {
        let configs = vec![
            WorkerConfig::required("python_worker", Some("https://python.internal".to_string())),
            WorkerConfig::optional("heavy_worker", Some("https://heavy.internal".to_string())),
        ];
        let summary = UpstreamHealthSummary {
            upstream_reachability: UpstreamReachability::Reachable,
            last_upstream_error: None,
            last_successful_contact_at_ms: Some(1),
            degraded: false,
            degraded_components: Vec::new(),
            worker_health: vec![
                WorkerHealthSnapshot {
                    worker_key: "python_worker".to_string(),
                    configured: true,
                    required: true,
                    base_url: Some("https://python.internal".to_string()),
                    reachability: UpstreamReachability::Reachable,
                    degraded: false,
                    last_successful_contact_at_ms: Some(1),
                    last_error: None,
                },
                WorkerHealthSnapshot {
                    worker_key: "heavy_worker".to_string(),
                    configured: true,
                    required: false,
                    base_url: Some("https://heavy.internal".to_string()),
                    reachability: UpstreamReachability::Unknown,
                    degraded: false,
                    last_successful_contact_at_ms: None,
                    last_error: None,
                },
            ],
        };

        let lifecycle = build_connector_lifecycle(&configs, &summary);
        assert!(lifecycle.degraded_mode.is_none());
        assert_eq!(lifecycle.connectors.len(), 2);
        assert_eq!(lifecycle.connectors[0].state, ConnectorState::Healthy);
        assert!(
            lifecycle.connectors[0]
                .available_capabilities
                .contains(&"operations.stream".to_string())
        );
        assert_eq!(lifecycle.connectors[1].state, ConnectorState::Unknown);
    }
}
