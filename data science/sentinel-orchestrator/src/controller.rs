use std::{
    collections::HashMap,
    sync::{
        Arc,
        atomic::{AtomicU64, Ordering},
    },
    time::{Duration, SystemTime, UNIX_EPOCH},
};

use axum::{Json, http::StatusCode};
use reqwest::header;
use serde_json::{Value, json};
use tokio::sync::{Mutex, Semaphore};
use tracing::{info, warn};

use crate::{
    config::AppState,
    contract::ControlPlaneActionResponse,
    correlation::CORRELATION_ID_HEADER,
    models::OperationEnvelope,
    policy::{
        DispatchLane, DispatchLease, OperationSnapshot, accepted_dispatch_decision,
        classify_dispatch_lane, duplicate_dispatch_decision, evaluate_dispatch_decision,
    },
    upstream::{
        HEAVY_WORKER_KEY, PYTHON_WORKER_KEY, UpstreamFailureKind, UpstreamFailureRecord,
        classify_reqwest_error,
    },
};

#[derive(Clone)]
pub struct DispatchController {
    active_leases: Arc<Mutex<HashMap<String, DispatchLease>>>,
    lease_sequence: Arc<AtomicU64>,
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

impl DispatchController {
    pub fn new(
        max_light_parallel: usize,
        max_heavy_parallel: usize,
        dispatch_timeout: Duration,
    ) -> Self {
        Self {
            active_leases: Arc::new(Mutex::new(HashMap::new())),
            lease_sequence: Arc::new(AtomicU64::new(0)),
            light_lane: Arc::new(Semaphore::new(max_light_parallel.max(1))),
            heavy_lane: Arc::new(Semaphore::new(max_heavy_parallel.max(1))),
            max_light_parallel: max_light_parallel.max(1),
            max_heavy_parallel: max_heavy_parallel.max(1),
            dispatch_timeout,
        }
    }

    pub async fn snapshot(&self) -> DispatchControllerSnapshot {
        let active_operations = self.active_operation_count().await;
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

    pub async fn active_leases_snapshot(&self) -> HashMap<String, DispatchLease> {
        let now_ms = now_ms();
        let mut leases = self.active_leases.lock().await;
        leases.retain(|_, lease| lease.is_active_at(now_ms));
        leases.clone()
    }

    pub async fn enqueue_dispatch(
        &self,
        state: AppState,
        operation_id: String,
        correlation_id: String,
    ) -> (StatusCode, Json<Value>) {
        match self.acquire_lease(&operation_id, &correlation_id).await {
            Ok(lease) => {
                let controller = self.clone();
                let spawn_lease = lease.clone();
                tokio::spawn(async move {
                    controller.run_dispatch(state, spawn_lease).await;
                });

                let decision = accepted_dispatch_decision(&lease.operation_id, &lease);
                let body =
                    serde_json::to_value(ControlPlaneActionResponse::from_dispatch_decision(
                        &decision,
                        &lease.correlation_id,
                    ))
                    .unwrap_or_else(|_| json!({}));
                (StatusCode::ACCEPTED, Json(body))
            }
            Err(existing_lease) => {
                let decision = duplicate_dispatch_decision(&operation_id, &existing_lease);
                let body =
                    serde_json::to_value(ControlPlaneActionResponse::from_dispatch_decision(
                        &decision,
                        &existing_lease.correlation_id,
                    ))
                    .unwrap_or_else(|_| json!({}));
                (StatusCode::ACCEPTED, Json(body))
            }
        }
    }

    async fn run_dispatch(&self, state: AppState, lease: DispatchLease) {
        let operation_id = lease.operation_id.clone();
        let correlation_id = lease.correlation_id.clone();
        let _release = ActiveDispatchGuard::new(
            self.active_leases.clone(),
            operation_id.clone(),
            lease.lease_id,
        );

        let operation = match fetch_operation(&state, &operation_id, &correlation_id).await {
            Some(operation) => operation,
            None => return,
        };

        let lane = classify_dispatch_lane(&operation);
        self.set_lease_lane(&operation_id, lease.lease_id, lane)
            .await;

        let worker_target = resolve_worker_target(&state, &operation);
        let dispatch_decision =
            evaluate_dispatch_decision(&operation, worker_target.map(|(worker_key, _)| worker_key));

        match dispatch_decision.decision {
            crate::policy::DispatchDecisionKind::Accepted => {}
            crate::policy::DispatchDecisionKind::SkippedNotQueued => {
                info!(
                    correlation_id = %correlation_id,
                    operation_id = %operation_id,
                    current_state = %dispatch_decision.current_state,
                    reason = %dispatch_decision.reason,
                    "skipping dispatch because policy rejected dispatch"
                );
                return;
            }
            crate::policy::DispatchDecisionKind::WorkerUnavailable => {
                warn!(
                    correlation_id = %correlation_id,
                    operation_id = %operation_id,
                    lane = ?lane,
                    "skipping dispatch because no worker target is available"
                );
                return;
            }
            crate::policy::DispatchDecisionKind::AlreadyManaged => {
                return;
            }
        }

        let permit = match lane {
            DispatchLane::Light => self.light_lane.clone().acquire_owned().await,
            DispatchLane::Heavy => self.heavy_lane.clone().acquire_owned().await,
        };

        let _permit = match permit {
            Ok(permit) => permit,
            Err(error) => {
                warn!(
                    correlation_id = %correlation_id,
                    operation_id = %operation_id,
                    "failed to acquire dispatch permit: {}",
                    error
                );
                return;
            }
        };

        let Some((worker_key, base_url)) = worker_target else {
            warn!(
                correlation_id = %correlation_id,
                operation_id = %operation_id,
                "worker base url not configured"
            );
            return;
        };

        let dispatch_url = format!("{base_url}/internal/operations/{operation_id}/dispatch");
        let request = state
            .http_client
            .post(&dispatch_url)
            .header(header::CONTENT_TYPE, "application/json")
            .header("X-Internal-Job-Token", &state.config.internal_job_token)
            .header(CORRELATION_ID_HEADER, &correlation_id)
            .body("{}")
            .timeout(self.dispatch_timeout);

        match request.send().await {
            Ok(response) => {
                if !response.status().is_success() {
                    let failure = UpstreamFailureRecord::new(
                        UpstreamFailureKind::BadStatus,
                        format!(
                            "Worker returned non-success status {} while dispatching {}",
                            response.status(),
                            operation_id
                        ),
                    )
                    .with_status_code(response.status().as_u16());
                    state
                        .worker_health_registry
                        .record_failure(worker_key, failure)
                        .await;
                    warn!(
                        correlation_id = %correlation_id,
                        operation_id = %operation_id,
                        worker_key = %worker_key,
                        status = %response.status(),
                        "python worker rejected orchestrated dispatch"
                    );
                } else {
                    state
                        .worker_health_registry
                        .record_success(worker_key)
                        .await;
                }
            }
            Err(error) => {
                let failure = UpstreamFailureRecord::new(
                    classify_reqwest_error(&error, false),
                    format!(
                        "Failed to dispatch operation {} through worker {}: {}",
                        operation_id, worker_key, error
                    ),
                );
                state
                    .worker_health_registry
                    .record_failure(worker_key, failure)
                    .await;
                warn!(
                    correlation_id = %correlation_id,
                    operation_id = %operation_id,
                    worker_key = %worker_key,
                    "failed to dispatch operation through python worker: {}",
                    error
                );
            }
        }
    }

    async fn acquire_lease(
        &self,
        operation_id: &str,
        correlation_id: &str,
    ) -> Result<DispatchLease, DispatchLease> {
        let now_ms = now_ms();
        let ttl_ms = self.dispatch_timeout.as_millis() as u64;
        let mut leases = self.active_leases.lock().await;

        if let Some(existing) = leases.get(operation_id).cloned() {
            if existing.is_active_at(now_ms) {
                return Err(existing);
            }
        }

        let lease_id = self.lease_sequence.fetch_add(1, Ordering::Relaxed) + 1;
        let lease =
            DispatchLease::new(lease_id, operation_id, None, now_ms, ttl_ms, correlation_id);
        leases.insert(operation_id.to_string(), lease.clone());
        Ok(lease)
    }

    async fn set_lease_lane(&self, operation_id: &str, lease_id: u64, lane: DispatchLane) {
        let mut leases = self.active_leases.lock().await;
        if let Some(lease) = leases.get_mut(operation_id) {
            if lease.lease_id == lease_id {
                lease.lane = Some(lane);
            }
        }
    }

    async fn active_operation_count(&self) -> usize {
        let now_ms = now_ms();
        let mut leases = self.active_leases.lock().await;
        leases.retain(|_, lease| lease.is_active_at(now_ms));
        leases.len()
    }
}

async fn fetch_operation(
    state: &AppState,
    operation_id: &str,
    correlation_id: &str,
) -> Option<OperationSnapshot> {
    let base_url = state.config.python_worker_base_url.as_ref()?;
    let url = format!("{base_url}/internal/operations/{operation_id}");
    let request = state
        .http_client
        .get(&url)
        .header(header::CONTENT_TYPE, "application/json")
        .header("X-Internal-Job-Token", &state.config.internal_job_token)
        .header(CORRELATION_ID_HEADER, correlation_id);

    let response = match request.send().await {
        Ok(response) => response,
        Err(error) => {
            state
                .worker_health_registry
                .record_failure(
                    PYTHON_WORKER_KEY,
                    UpstreamFailureRecord::new(
                        classify_reqwest_error(&error, false),
                        format!(
                            "Failed to fetch operation {} before dispatch: {}",
                            operation_id, error
                        ),
                    ),
                )
                .await;
            warn!(
                correlation_id = %correlation_id,
                operation_id = %operation_id,
                "failed to fetch operation before dispatch: {}",
                error
            );
            return None;
        }
    };

    if !response.status().is_success() {
        state
            .worker_health_registry
            .record_failure(
                PYTHON_WORKER_KEY,
                UpstreamFailureRecord::new(
                    UpstreamFailureKind::BadStatus,
                    format!(
                        "Failed to fetch operation {} before dispatch: status {}",
                        operation_id,
                        response.status()
                    ),
                )
                .with_status_code(response.status().as_u16()),
            )
            .await;
        warn!(
            correlation_id = %correlation_id,
            operation_id = %operation_id,
            status = %response.status(),
            "failed to fetch operation before dispatch"
        );
        return None;
    }

    match response
        .json::<OperationEnvelope<OperationSnapshot>>()
        .await
    {
        Ok(envelope) => {
            state
                .worker_health_registry
                .record_success(PYTHON_WORKER_KEY)
                .await;
            Some(envelope.data)
        }
        Err(error) => {
            state
                .worker_health_registry
                .record_failure(
                    PYTHON_WORKER_KEY,
                    UpstreamFailureRecord::new(
                        UpstreamFailureKind::DecodeError,
                        format!(
                            "Failed to decode operation {} envelope before dispatch: {}",
                            operation_id, error
                        ),
                    ),
                )
                .await;
            warn!(
                correlation_id = %correlation_id,
                operation_id = %operation_id,
                "failed to decode operation envelope: {}",
                error
            );
            None
        }
    }
}

fn resolve_worker_target<'a>(
    state: &'a AppState,
    operation: &OperationSnapshot,
) -> Option<(&'static str, &'a String)> {
    match operation.execution_target.as_str() {
        "heavy_worker" => state
            .config
            .heavy_worker_base_url
            .as_ref()
            .map(|url| (HEAVY_WORKER_KEY, url))
            .or_else(|| {
                state
                    .config
                    .python_worker_base_url
                    .as_ref()
                    .map(|url| (PYTHON_WORKER_KEY, url))
            }),
        _ => state
            .config
            .python_worker_base_url
            .as_ref()
            .map(|url| (PYTHON_WORKER_KEY, url)),
    }
}

fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}

struct ActiveDispatchGuard {
    active_leases: Arc<Mutex<HashMap<String, DispatchLease>>>,
    operation_id: String,
    lease_id: u64,
}

impl ActiveDispatchGuard {
    fn new(
        active_leases: Arc<Mutex<HashMap<String, DispatchLease>>>,
        operation_id: String,
        lease_id: u64,
    ) -> Self {
        Self {
            active_leases,
            operation_id,
            lease_id,
        }
    }
}

impl Drop for ActiveDispatchGuard {
    fn drop(&mut self) {
        let active_leases = self.active_leases.clone();
        let operation_id = self.operation_id.clone();
        let lease_id = self.lease_id;
        tokio::spawn(async move {
            let mut leases = active_leases.lock().await;
            if leases
                .get(&operation_id)
                .is_some_and(|lease| lease.lease_id == lease_id)
            {
                leases.remove(&operation_id);
            }
        });
    }
}
