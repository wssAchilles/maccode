use reqwest::header;
use serde::{Deserialize, Serialize};
use tracing::warn;

use crate::{config::AppState, models::OperationEnvelope};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComputeAccelerationTelemetry {
    pub status: String,
    pub message: String,
    pub active_backend: String,
    pub preferred_backend: String,
    pub native_enabled: bool,
    pub native_available: bool,
    pub profiled_components: usize,
    pub benchmark_ready: bool,
    pub hottest_component: String,
    pub last_updated_at: String,
    #[serde(default)]
    pub rollout: ComputeRolloutTelemetry,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComputeRolloutTelemetry {
    pub enabled: bool,
    pub updated_at: String,
    pub updated_by: String,
    pub components: Vec<ComputeRolloutComponentTelemetry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComputeRolloutComponentTelemetry {
    pub key: String,
    pub label: String,
    pub rollout_mode: String,
    pub preferred_backend: String,
    pub canary_percent: u8,
    pub require_benchmark: bool,
    pub last_benchmark_at: String,
    pub last_benchmark_context: String,
    pub last_benchmark_backend: String,
    pub notes: String,
}

impl ComputeAccelerationTelemetry {
    fn unavailable(message: &str) -> Self {
        Self {
            status: "warning".to_string(),
            message: message.to_string(),
            active_backend: "python_pandas".to_string(),
            preferred_backend: "python_pandas".to_string(),
            native_enabled: false,
            native_available: false,
            profiled_components: 0,
            benchmark_ready: false,
            hottest_component: "--".to_string(),
            last_updated_at: String::new(),
            rollout: ComputeRolloutTelemetry::unavailable(),
        }
    }
}

impl ComputeRolloutTelemetry {
    pub fn unavailable() -> Self {
        Self {
            enabled: false,
            updated_at: String::new(),
            updated_by: String::new(),
            components: Vec::new(),
        }
    }
}

impl Default for ComputeRolloutTelemetry {
    fn default() -> Self {
        Self::unavailable()
    }
}

pub async fn fetch_compute_acceleration(state: &AppState) -> ComputeAccelerationTelemetry {
    let Some(base_url) = state.config.python_worker_base_url.as_ref() else {
        return ComputeAccelerationTelemetry::unavailable(
            "Python worker not configured for compute telemetry",
        );
    };

    let url = format!("{base_url}/internal/runtime/compute-status");
    let request = state
        .http_client
        .get(&url)
        .header(header::ACCEPT, "application/json")
        .header("X-Internal-Job-Token", &state.config.internal_job_token);

    let response = match request.send().await {
        Ok(response) => response,
        Err(error) => {
            warn!("failed to fetch compute telemetry from {}: {}", url, error);
            return ComputeAccelerationTelemetry::unavailable(
                "Compute telemetry unavailable through python worker",
            );
        }
    };

    if !response.status().is_success() {
        warn!(
            "python worker compute telemetry returned non-success status {}",
            response.status()
        );
        return ComputeAccelerationTelemetry::unavailable(
            "Compute telemetry endpoint returned non-success status",
        );
    }

    match response
        .json::<OperationEnvelope<ComputeAccelerationTelemetry>>()
        .await
    {
        Ok(envelope) => envelope.data,
        Err(error) => {
            warn!("failed to decode compute telemetry envelope: {}", error);
            ComputeAccelerationTelemetry::unavailable("Compute telemetry payload decode failed")
        }
    }
}

pub async fn fetch_compute_rollout(state: &AppState) -> ComputeRolloutTelemetry {
    let Some(base_url) = state.config.python_worker_base_url.as_ref() else {
        return ComputeRolloutTelemetry::unavailable();
    };

    let url = format!("{base_url}/internal/compute/rollout");
    let request = state
        .http_client
        .get(&url)
        .header(header::ACCEPT, "application/json")
        .header("X-Internal-Job-Token", &state.config.internal_job_token);

    let response = match request.send().await {
        Ok(response) => response,
        Err(error) => {
            warn!("failed to fetch compute rollout from {}: {}", url, error);
            return ComputeRolloutTelemetry::unavailable();
        }
    };

    if !response.status().is_success() {
        warn!(
            "python worker compute rollout returned non-success status {}",
            response.status()
        );
        return ComputeRolloutTelemetry::unavailable();
    }

    match response
        .json::<OperationEnvelope<ComputeRolloutTelemetry>>()
        .await
    {
        Ok(envelope) => envelope.data,
        Err(error) => {
            warn!("failed to decode compute rollout envelope: {}", error);
            ComputeRolloutTelemetry::unavailable()
        }
    }
}
