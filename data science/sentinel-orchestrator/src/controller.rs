use std::{collections::HashSet, sync::Arc, time::Duration};

use axum::{Json, http::StatusCode};
use reqwest::header;
use serde::Deserialize;
use serde_json::{Value, json};
use tokio::sync::{Mutex, Semaphore};
use tracing::{info, warn};

use crate::{config::AppState, models::OperationEnvelope};

#[derive(Clone)]
pub struct DispatchController {
    active_operations: Arc<Mutex<HashSet<String>>>,
    light_lane: Arc<Semaphore>,
    heavy_lane: Arc<Semaphore>,
    max_light_parallel: usize,
    max_heavy_parallel: usize,
    dispatch_timeout: Duration,
}

#[derive(Debug, Clone)]
pub struct DispatchControllerSnapshot {
    pub active_operations: usize,
    pub light_capacity: usize,
    pub light_available: usize,
    pub heavy_capacity: usize,
    pub heavy_available: usize,
    pub dispatch_timeout_secs: u64,
}

#[derive(Debug, Clone, Deserialize)]
struct OperationRecord {
    #[serde(default)]
    r#type: String,
    #[serde(default)]
    status: String,
    #[serde(default)]
    execution_target: String,
}

#[derive(Debug, Clone, Copy)]
enum DispatchLane {
    Light,
    Heavy,
}

impl DispatchController {
    pub fn new(
        max_light_parallel: usize,
        max_heavy_parallel: usize,
        dispatch_timeout: Duration,
    ) -> Self {
        Self {
            active_operations: Arc::new(Mutex::new(HashSet::new())),
            light_lane: Arc::new(Semaphore::new(max_light_parallel.max(1))),
            heavy_lane: Arc::new(Semaphore::new(max_heavy_parallel.max(1))),
            max_light_parallel: max_light_parallel.max(1),
            max_heavy_parallel: max_heavy_parallel.max(1),
            dispatch_timeout,
        }
    }

    pub async fn snapshot(&self) -> DispatchControllerSnapshot {
        let active_operations = self.active_operations.lock().await.len();
        let light_available = self.light_lane.available_permits();
        let heavy_available = self.heavy_lane.available_permits();
        DispatchControllerSnapshot {
            active_operations,
            light_capacity: self.max_light_parallel,
            light_available,
            heavy_capacity: self.max_heavy_parallel,
            heavy_available,
            dispatch_timeout_secs: self.dispatch_timeout.as_secs(),
        }
    }

    pub async fn enqueue_dispatch(
        &self,
        state: AppState,
        operation_id: String,
    ) -> (StatusCode, Json<Value>) {
        {
            let mut active = self.active_operations.lock().await;
            if !active.insert(operation_id.clone()) {
                return (
                    StatusCode::ACCEPTED,
                    Json(json!({
                        "operation_id": operation_id,
                        "status": "already_dispatching",
                    })),
                );
            }
        }

        let controller = self.clone();
        tokio::spawn(async move {
            controller.run_dispatch(state, operation_id).await;
        });

        (
            StatusCode::ACCEPTED,
            Json(json!({
                "status": "accepted",
                "message": "Dispatch queued in orchestrator",
            })),
        )
    }

    async fn run_dispatch(&self, state: AppState, operation_id: String) {
        let release =
            ActiveDispatchGuard::new(self.active_operations.clone(), operation_id.clone());

        let operation = match fetch_operation(&state, &operation_id).await {
            Some(operation) => operation,
            None => return,
        };

        if operation.status != "queued" {
            info!(
                operation_id = %operation_id,
                status = %operation.status,
                "skipping dispatch because operation is not queued"
            );
            drop(release);
            return;
        }

        let lane = classify_lane(&operation.r#type, &operation.execution_target);
        let permit = match lane {
            DispatchLane::Light => self.light_lane.clone().acquire_owned().await,
            DispatchLane::Heavy => self.heavy_lane.clone().acquire_owned().await,
        };

        let _permit = match permit {
            Ok(permit) => permit,
            Err(error) => {
                warn!(operation_id = %operation_id, "failed to acquire dispatch permit: {}", error);
                drop(release);
                return;
            }
        };

        let Some(base_url) = resolve_worker_base_url(&state, &operation) else {
            warn!(operation_id = %operation_id, "worker base url not configured");
            drop(release);
            return;
        };

        let dispatch_url = format!("{base_url}/internal/operations/{operation_id}/dispatch");
        let request = state
            .http_client
            .post(&dispatch_url)
            .header(header::CONTENT_TYPE, "application/json")
            .header("X-Internal-Job-Token", &state.config.internal_job_token)
            .body("{}")
            .timeout(self.dispatch_timeout);

        match request.send().await {
            Ok(response) => {
                if !response.status().is_success() {
                    warn!(
                        operation_id = %operation_id,
                        status = %response.status(),
                        "python worker rejected orchestrated dispatch"
                    );
                }
            }
            Err(error) => {
                warn!(
                    operation_id = %operation_id,
                    "failed to dispatch operation through python worker: {}",
                    error
                );
            }
        }

        drop(release);
    }
}

async fn fetch_operation(state: &AppState, operation_id: &str) -> Option<OperationRecord> {
    let base_url = state.config.python_worker_base_url.as_ref()?;
    let url = format!("{base_url}/internal/operations/{operation_id}");
    let request = state
        .http_client
        .get(&url)
        .header(header::CONTENT_TYPE, "application/json")
        .header("X-Internal-Job-Token", &state.config.internal_job_token);

    let response = match request.send().await {
        Ok(response) => response,
        Err(error) => {
            warn!(operation_id = %operation_id, "failed to fetch operation before dispatch: {}", error);
            return None;
        }
    };

    if !response.status().is_success() {
        warn!(
            operation_id = %operation_id,
            status = %response.status(),
            "failed to fetch operation before dispatch"
        );
        return None;
    }

    match response.json::<OperationEnvelope<OperationRecord>>().await {
        Ok(envelope) => Some(envelope.data),
        Err(error) => {
            warn!(operation_id = %operation_id, "failed to decode operation envelope: {}", error);
            None
        }
    }
}

fn classify_lane(operation_type: &str, execution_target: &str) -> DispatchLane {
    if execution_target == "heavy_worker" {
        return DispatchLane::Heavy;
    }
    match operation_type {
        "ml_train" | "rag_ingest" => DispatchLane::Heavy,
        _ => DispatchLane::Light,
    }
}

fn resolve_worker_base_url<'a>(
    state: &'a AppState,
    operation: &OperationRecord,
) -> Option<&'a String> {
    match operation.execution_target.as_str() {
        "heavy_worker" => state
            .config
            .heavy_worker_base_url
            .as_ref()
            .or(state.config.python_worker_base_url.as_ref()),
        _ => state.config.python_worker_base_url.as_ref(),
    }
}

struct ActiveDispatchGuard {
    active_operations: Arc<Mutex<HashSet<String>>>,
    operation_id: String,
}

impl ActiveDispatchGuard {
    fn new(active_operations: Arc<Mutex<HashSet<String>>>, operation_id: String) -> Self {
        Self {
            active_operations,
            operation_id,
        }
    }
}

impl Drop for ActiveDispatchGuard {
    fn drop(&mut self) {
        let active_operations = self.active_operations.clone();
        let operation_id = self.operation_id.clone();
        tokio::spawn(async move {
            let mut active = active_operations.lock().await;
            active.remove(&operation_id);
        });
    }
}
