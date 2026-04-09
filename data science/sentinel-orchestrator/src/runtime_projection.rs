use std::{
    collections::HashMap,
    sync::Arc,
    time::{SystemTime, UNIX_EPOCH},
};

use reqwest::header;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use time::OffsetDateTime;
use time::format_description::well_known::Rfc3339;
use tokio::sync::RwLock;
use tracing::warn;

use crate::{
    config::AppState,
    connector::{ConnectorDegradedMode, ConnectorHealthcheck, build_connector_lifecycle},
    controller::DispatchControllerSnapshot,
    correlation::CORRELATION_ID_HEADER,
    policy::{
        ApprovalStateSnapshot, CONTROL_PLANE_MANAGER, CONTROL_PLANE_POLICY_VERSION, DispatchLane,
        DispatchLease, OperationSnapshot, classify_dispatch_lane,
    },
    upstream::{
        PYTHON_WORKER_KEY, UpstreamFailureKind, UpstreamFailureRecord, UpstreamReachability,
        WorkerHealthSnapshot, classify_reqwest_error,
    },
};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RuntimeProjectionSnapshot {
    pub projection_version: String,
    pub generated_at: String,
    pub requested_for: String,
    pub control_plane: RuntimeControlPlaneSummary,
    pub control_tasks: RuntimeControlTaskSection,
    #[serde(default)]
    pub degraded_sections: Vec<RuntimeProjectionDegradedSection>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RuntimeControlPlaneSummary {
    pub managed_by: String,
    pub policy_version: String,
    pub active_operations: usize,
    pub queue_depth: usize,
    pub dispatch_timeout_secs: u64,
    pub light_lane: RuntimeLaneStatus,
    pub heavy_lane: RuntimeLaneStatus,
    pub upstream_reachability: UpstreamReachability,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_upstream_error: Option<UpstreamFailureRecord>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_successful_contact_at_ms: Option<u64>,
    pub degraded: bool,
    #[serde(default)]
    pub degraded_components: Vec<String>,
    #[serde(default)]
    pub worker_health: Vec<WorkerHealthSnapshot>,
    #[serde(default)]
    pub connectors: Vec<ConnectorHealthcheck>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub degraded_mode: Option<ConnectorDegradedMode>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_correlation_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RuntimeLaneStatus {
    pub capacity: usize,
    pub available: usize,
    pub in_use: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RuntimeControlTaskSection {
    #[serde(default)]
    pub items: Vec<RuntimeControlTaskRecord>,
    pub count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RuntimeControlTaskRecord {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub kind: String,
    #[serde(default)]
    pub operation_type: String,
    #[serde(default)]
    pub title: String,
    #[serde(default)]
    pub schedule: Option<String>,
    #[serde(default)]
    pub default_input: HashMap<String, Value>,
    #[serde(default)]
    pub dependencies: Vec<String>,
    #[serde(default)]
    pub approval_policy: HashMap<String, Value>,
    #[serde(default = "default_enabled")]
    pub enabled: bool,
    #[serde(default)]
    pub owner: String,
    #[serde(default)]
    pub next_run_at: Option<String>,
    #[serde(default)]
    pub dependency_state: String,
    #[serde(default)]
    pub dependency_summary: String,
    #[serde(default)]
    pub dependency_details: Vec<RuntimeControlTaskDependencyDetail>,
    #[serde(default)]
    pub latest_operation: Option<RuntimeControlTaskLatestOperation>,
    #[serde(default)]
    pub created_at: Option<String>,
    #[serde(default)]
    pub updated_at: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub control_plane_projection: Option<RuntimeControlTaskProjection>,
    #[serde(flatten)]
    pub extra: HashMap<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RuntimeControlTaskDependencyDetail {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub state: String,
    #[serde(default)]
    pub title: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RuntimeControlTaskLatestOperation {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub job_id: String,
    #[serde(default)]
    pub operation_id: String,
    #[serde(default)]
    pub r#type: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub progress: i64,
    #[serde(default)]
    pub execution_target: String,
    #[serde(default)]
    pub submitted_at: Option<String>,
    #[serde(default)]
    pub approval_state: ApprovalStateSnapshot,
    #[serde(default)]
    pub session_projection: RuntimeSessionProjection,
    #[serde(flatten)]
    pub extra: HashMap<String, Value>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct RuntimeSessionProjection {
    #[serde(default)]
    pub phase: String,
    #[serde(default)]
    pub latest_event_type: Option<String>,
    #[serde(default)]
    pub latest_event_message: Option<String>,
    #[serde(default)]
    pub latest_event_at: Option<String>,
    #[serde(default)]
    pub last_transition_at: Option<String>,
    #[serde(default)]
    pub current_step_label: Option<String>,
    #[serde(default)]
    pub event_count: usize,
    #[serde(default)]
    pub step_count: usize,
    #[serde(default)]
    pub artifact_count: usize,
    #[serde(default)]
    pub stream_recommended: bool,
    #[serde(default)]
    pub terminal: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RuntimeControlTaskProjection {
    pub managed_by: String,
    pub policy_version: String,
    pub runtime_state: String,
    pub awaiting_approval: bool,
    pub in_flight_lock: bool,
    pub eligible_now: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub next_eligible_run: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_operation_state: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_failure_reason: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub latest_event_message: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub dispatch_lane: Option<DispatchLane>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub lease_expires_at_ms: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub correlation_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RuntimeProjectionDegradedSection {
    pub section: String,
    pub message: String,
}

#[derive(Clone, Default)]
pub struct RuntimeProjectionCache {
    inner: Arc<RwLock<Option<CachedRuntimeProjection>>>,
}

#[derive(Debug, Clone)]
struct CachedRuntimeProjection {
    cached_at_ms: u64,
    ttl_ms: u64,
    snapshot: RuntimeProjectionSnapshot,
}

impl RuntimeProjectionCache {
    pub async fn get(&self, now_ms: u64) -> Option<RuntimeProjectionSnapshot> {
        let cache = self.inner.read().await;
        let snapshot = cache.as_ref()?;
        if now_ms.saturating_sub(snapshot.cached_at_ms) > snapshot.ttl_ms {
            return None;
        }
        Some(snapshot.snapshot.clone())
    }

    pub async fn set(&self, snapshot: RuntimeProjectionSnapshot, ttl_ms: u64) {
        let mut cache = self.inner.write().await;
        *cache = Some(CachedRuntimeProjection {
            cached_at_ms: now_ms(),
            ttl_ms,
            snapshot,
        });
    }
}

pub async fn get_runtime_projection(
    state: &AppState,
    uid: &str,
    force_refresh: bool,
) -> RuntimeProjectionSnapshot {
    let ttl_ms = state.config.runtime_snapshot_ttl_secs.saturating_mul(1000);
    let now = now_ms();
    if !force_refresh && ttl_ms > 0 {
        if let Some(snapshot) = state.runtime_projection_cache.get(now).await {
            return snapshot;
        }
    }

    let snapshot = build_runtime_projection(state, uid).await;
    if ttl_ms > 0 {
        state
            .runtime_projection_cache
            .set(snapshot.clone(), ttl_ms)
            .await;
    }
    snapshot
}

async fn build_runtime_projection(state: &AppState, uid: &str) -> RuntimeProjectionSnapshot {
    let controller_snapshot = state.dispatch_controller.snapshot().await;
    let active_leases = state.dispatch_controller.active_leases_snapshot().await;
    let worker_health_summary = state
        .worker_health_registry
        .summary(&state.config.worker_configs())
        .await;
    let connector_lifecycle =
        build_connector_lifecycle(&state.config.worker_configs(), &worker_health_summary);

    let mut degraded_sections = Vec::new();
    let mut control_tasks = match fetch_control_tasks(state).await {
        Ok(tasks) => tasks,
        Err(degraded) => {
            degraded_sections.push(degraded);
            Vec::new()
        }
    };

    for task in &mut control_tasks {
        let operation_id = task.latest_operation_id();
        let lease = operation_id
            .as_deref()
            .and_then(|current_operation_id| active_leases.get(current_operation_id));
        task.control_plane_projection = Some(build_task_projection(task, lease));
    }

    if worker_health_summary.degraded {
        let message = if let Some(error) = worker_health_summary.last_upstream_error.as_ref() {
            format!(
                "Control-plane degraded: {} ({})",
                error.message,
                error.kind.error_code()
            )
        } else {
            format!(
                "Control-plane degraded: {}",
                worker_health_summary.degraded_components.join(", ")
            )
        };
        degraded_sections.push(RuntimeProjectionDegradedSection {
            section: "control_plane".to_string(),
            message,
        });
    }

    let queue_depth = control_tasks
        .iter()
        .filter(|task| {
            task.control_plane_projection
                .as_ref()
                .is_some_and(|projection| projection.in_flight_lock || projection.awaiting_approval)
        })
        .count();

    RuntimeProjectionSnapshot {
        projection_version: "control-plane-runtime-v1".to_string(),
        generated_at: utc_now_iso(),
        requested_for: uid.to_string(),
        control_plane: build_control_plane_summary(
            state,
            controller_snapshot,
            worker_health_summary,
            connector_lifecycle,
            queue_depth,
        ),
        control_tasks: RuntimeControlTaskSection {
            count: control_tasks.len(),
            items: control_tasks,
        },
        degraded_sections,
    }
}

async fn fetch_control_tasks(
    state: &AppState,
) -> Result<Vec<RuntimeControlTaskRecord>, RuntimeProjectionDegradedSection> {
    let Some(base_url) = state.config.python_worker_base_url.as_ref() else {
        return Err(RuntimeProjectionDegradedSection {
            section: "control_tasks_projection".to_string(),
            message: "PYTHON_WORKER_BASE_URL is not configured".to_string(),
        });
    };

    let url = format!("{base_url}/internal/control-tasks");
    let correlation_id = state.correlation_ids.generate();
    let request = state
        .http_client
        .get(&url)
        .header(header::ACCEPT, "application/json")
        .header("X-Internal-Job-Token", &state.config.internal_job_token)
        .header(CORRELATION_ID_HEADER, &correlation_id);

    let response = match request.send().await {
        Ok(response) => response,
        Err(error) => {
            state
                .worker_health_registry
                .record_failure(
                    PYTHON_WORKER_KEY,
                    UpstreamFailureRecord::new(
                        classify_reqwest_error(&error, false),
                        format!("Failed to fetch control-task projection from {url}: {error}"),
                    ),
                )
                .await;
            warn!(
                "failed to fetch control-task projection from {}: {}",
                url, error
            );
            return Err(RuntimeProjectionDegradedSection {
                section: "control_tasks_projection".to_string(),
                message: format!("Failed to fetch control-task projection: {error}"),
            });
        }
    };

    if !response.status().is_success() {
        let failure = UpstreamFailureRecord::new(
            UpstreamFailureKind::BadStatus,
            format!(
                "Control-task projection endpoint returned non-success status {}",
                response.status()
            ),
        )
        .with_status_code(response.status().as_u16());
        state
            .worker_health_registry
            .record_failure(PYTHON_WORKER_KEY, failure)
            .await;
        return Err(RuntimeProjectionDegradedSection {
            section: "control_tasks_projection".to_string(),
            message: format!(
                "Control-task projection endpoint returned {}",
                response.status()
            ),
        });
    }

    match response.json::<Value>().await {
        Ok(payload) => match decode_control_task_records(&payload) {
            Some(tasks) => {
                state
                    .worker_health_registry
                    .record_success(PYTHON_WORKER_KEY)
                    .await;
                Ok(tasks)
            }
            None => {
                state
                    .worker_health_registry
                    .record_failure(
                        PYTHON_WORKER_KEY,
                        UpstreamFailureRecord::new(
                            UpstreamFailureKind::DecodeError,
                            format!(
                                "Control-task projection payload shape was incompatible for {url}"
                            ),
                        ),
                    )
                    .await;
                Err(RuntimeProjectionDegradedSection {
                    section: "control_tasks_projection".to_string(),
                    message: "Failed to decode control-task projection payload shape".to_string(),
                })
            }
        },
        Err(error) => {
            state
                .worker_health_registry
                .record_failure(
                    PYTHON_WORKER_KEY,
                    UpstreamFailureRecord::new(
                        UpstreamFailureKind::DecodeError,
                        format!("Failed to decode control-task projection from {url}: {error}"),
                    ),
                )
                .await;
            Err(RuntimeProjectionDegradedSection {
                section: "control_tasks_projection".to_string(),
                message: format!("Failed to decode control-task projection: {error}"),
            })
        }
    }
}

fn build_control_plane_summary(
    state: &AppState,
    controller_snapshot: DispatchControllerSnapshot,
    worker_health_summary: crate::upstream::UpstreamHealthSummary,
    connector_lifecycle: crate::connector::ConnectorLifecycleSnapshot,
    queue_depth: usize,
) -> RuntimeControlPlaneSummary {
    RuntimeControlPlaneSummary {
        managed_by: CONTROL_PLANE_MANAGER.to_string(),
        policy_version: CONTROL_PLANE_POLICY_VERSION.to_string(),
        active_operations: controller_snapshot.active_operations,
        queue_depth,
        dispatch_timeout_secs: controller_snapshot.dispatch_timeout_secs,
        light_lane: RuntimeLaneStatus {
            capacity: controller_snapshot.light_capacity,
            available: controller_snapshot.light_available,
            in_use: controller_snapshot
                .light_capacity
                .saturating_sub(controller_snapshot.light_available),
        },
        heavy_lane: RuntimeLaneStatus {
            capacity: controller_snapshot.heavy_capacity,
            available: controller_snapshot.heavy_available,
            in_use: controller_snapshot
                .heavy_capacity
                .saturating_sub(controller_snapshot.heavy_available),
        },
        upstream_reachability: worker_health_summary.upstream_reachability,
        last_upstream_error: worker_health_summary.last_upstream_error,
        last_successful_contact_at_ms: worker_health_summary.last_successful_contact_at_ms,
        degraded: worker_health_summary.degraded,
        degraded_components: worker_health_summary.degraded_components,
        worker_health: worker_health_summary.worker_health,
        connectors: connector_lifecycle.connectors,
        degraded_mode: connector_lifecycle.degraded_mode,
        last_correlation_id: state.correlation_ids.last_issued(),
    }
}

fn build_task_projection(
    task: &RuntimeControlTaskRecord,
    lease: Option<&DispatchLease>,
) -> RuntimeControlTaskProjection {
    let latest_operation = task.latest_operation.as_ref();
    let last_operation_state = latest_operation
        .map(|operation| operation.status.trim().to_string())
        .filter(|status| !status.is_empty());
    let awaiting_approval =
        latest_operation.is_some_and(RuntimeControlTaskLatestOperation::is_awaiting_approval);
    let in_flight_lock = lease.is_some()
        || last_operation_state.as_deref().is_some_and(|status| {
            matches!(status, "queued" | "dispatching" | "running" | "retrying")
        });
    let latest_event_message = latest_operation.and_then(|operation| {
        operation
            .session_projection
            .latest_event_message
            .clone()
            .filter(|message| !message.trim().is_empty())
    });
    let last_failure_reason = last_operation_state
        .as_deref()
        .filter(|status| *status == "failed")
        .and(latest_event_message.clone());
    let dispatch_lane = lease
        .and_then(|active| active.lane)
        .or_else(|| classify_task_lane(task));
    let dependencies_ready = task.dependencies_ready();
    let eligible_now = task.enabled
        && dependencies_ready
        && !awaiting_approval
        && !in_flight_lock
        && task.next_run_at.is_none();
    let next_eligible_run =
        if task.enabled && dependencies_ready && !awaiting_approval && !in_flight_lock {
            task.next_run_at.clone()
        } else {
            None
        };

    RuntimeControlTaskProjection {
        managed_by: CONTROL_PLANE_MANAGER.to_string(),
        policy_version: CONTROL_PLANE_POLICY_VERSION.to_string(),
        runtime_state: classify_runtime_state(
            task.enabled,
            dependencies_ready,
            awaiting_approval,
            in_flight_lock,
            last_operation_state.as_deref(),
            task.next_run_at.as_deref(),
        ),
        awaiting_approval,
        in_flight_lock,
        eligible_now,
        next_eligible_run,
        last_operation_state,
        last_failure_reason,
        latest_event_message,
        dispatch_lane,
        lease_expires_at_ms: lease.map(|active| active.expires_at_ms),
        correlation_id: lease.map(|active| active.correlation_id.clone()),
    }
}

fn classify_runtime_state(
    enabled: bool,
    dependencies_ready: bool,
    awaiting_approval: bool,
    in_flight_lock: bool,
    last_operation_state: Option<&str>,
    next_run_at: Option<&str>,
) -> String {
    if !enabled {
        return "disabled".to_string();
    }
    if !dependencies_ready {
        return "dependency_blocked".to_string();
    }
    if awaiting_approval {
        return "awaiting_approval".to_string();
    }
    if in_flight_lock {
        return "in_flight".to_string();
    }
    if last_operation_state.is_some_and(|status| status == "failed") {
        return "attention_required".to_string();
    }
    if next_run_at.is_some() {
        return "scheduled".to_string();
    }
    "ready".to_string()
}

fn classify_task_lane(task: &RuntimeControlTaskRecord) -> Option<DispatchLane> {
    let latest_operation = task.latest_operation.as_ref();
    let operation_type = if !task.operation_type.trim().is_empty() {
        task.operation_type.clone()
    } else {
        latest_operation
            .map(|operation| operation.r#type.clone())
            .unwrap_or_default()
    };
    let execution_target = latest_operation
        .map(|operation| operation.execution_target.clone())
        .unwrap_or_default();
    if operation_type.is_empty() && execution_target.is_empty() {
        return None;
    }
    let snapshot = OperationSnapshot {
        id: latest_operation
            .map(RuntimeControlTaskLatestOperation::resolved_operation_id)
            .unwrap_or_default(),
        job_id: latest_operation
            .map(RuntimeControlTaskLatestOperation::resolved_operation_id)
            .unwrap_or_default(),
        r#type: operation_type,
        status: latest_operation
            .map(|operation| operation.status.clone())
            .unwrap_or_else(|| "queued".to_string()),
        execution_target,
        control_task_id: Some(task.id.clone()),
        approval_state: latest_operation
            .map(|operation| operation.approval_state.clone())
            .unwrap_or_default(),
    };
    Some(classify_dispatch_lane(&snapshot))
}

impl RuntimeControlTaskRecord {
    fn latest_operation_id(&self) -> Option<String> {
        self.latest_operation
            .as_ref()
            .map(RuntimeControlTaskLatestOperation::resolved_operation_id)
            .filter(|operation_id| !operation_id.trim().is_empty())
    }

    fn dependencies_ready(&self) -> bool {
        matches!(self.dependency_state.as_str(), "" | "none" | "ready")
    }
}

impl RuntimeControlTaskLatestOperation {
    fn resolved_operation_id(&self) -> String {
        if !self.operation_id.trim().is_empty() {
            return self.operation_id.clone();
        }
        if !self.job_id.trim().is_empty() {
            return self.job_id.clone();
        }
        self.id.clone()
    }

    fn is_awaiting_approval(&self) -> bool {
        self.status == "awaiting_approval" || self.approval_state.state == "pending"
    }
}

fn default_enabled() -> bool {
    true
}

fn decode_control_task_records(payload: &Value) -> Option<Vec<RuntimeControlTaskRecord>> {
    let data = payload.get("data")?;
    if data.is_array() {
        return serde_json::from_value::<Vec<RuntimeControlTaskRecord>>(data.clone()).ok();
    }
    if let Some(items) = data.get("control_tasks") {
        return serde_json::from_value::<Vec<RuntimeControlTaskRecord>>(items.clone()).ok();
    }
    if let Some(items) = data.get("items") {
        return serde_json::from_value::<Vec<RuntimeControlTaskRecord>>(items.clone()).ok();
    }
    None
}

fn utc_now_iso() -> String {
    OffsetDateTime::now_utc()
        .format(&Rfc3339)
        .unwrap_or_else(|_| String::new())
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

    fn sample_task() -> RuntimeControlTaskRecord {
        RuntimeControlTaskRecord {
            id: "train-model-daily".to_string(),
            kind: "scheduler".to_string(),
            operation_type: "ml_train".to_string(),
            title: "Train model daily".to_string(),
            schedule: Some("every day 04:00 UTC".to_string()),
            default_input: HashMap::new(),
            dependencies: vec!["dataset-ready".to_string()],
            approval_policy: HashMap::new(),
            enabled: true,
            owner: "system".to_string(),
            next_run_at: Some("2026-04-10T04:00:00+00:00".to_string()),
            dependency_state: "ready".to_string(),
            dependency_summary: "依赖已就绪".to_string(),
            dependency_details: Vec::new(),
            latest_operation: Some(RuntimeControlTaskLatestOperation {
                id: String::new(),
                job_id: "op-1".to_string(),
                operation_id: "op-1".to_string(),
                r#type: "ml_train".to_string(),
                status: "awaiting_approval".to_string(),
                progress: 0,
                execution_target: "heavy_worker".to_string(),
                submitted_at: Some("2026-04-09T10:00:00+00:00".to_string()),
                approval_state: ApprovalStateSnapshot {
                    state: "pending".to_string(),
                    required: true,
                },
                session_projection: RuntimeSessionProjection {
                    latest_event_message: Some("Waiting for manual approval".to_string()),
                    ..RuntimeSessionProjection::default()
                },
                extra: HashMap::new(),
            }),
            created_at: None,
            updated_at: None,
            control_plane_projection: None,
            extra: HashMap::new(),
        }
    }

    #[test]
    fn task_projection_marks_awaiting_approval_and_lane() {
        let task = sample_task();

        let projection = build_task_projection(&task, None);

        assert_eq!(projection.runtime_state, "awaiting_approval");
        assert!(projection.awaiting_approval);
        assert_eq!(projection.dispatch_lane, Some(DispatchLane::Heavy));
        assert_eq!(projection.next_eligible_run, None);
    }

    #[test]
    fn task_projection_uses_active_lease_for_in_flight_lock() {
        let mut task = sample_task();
        task.latest_operation.as_mut().expect("latest op").status = "queued".to_string();
        task.latest_operation
            .as_mut()
            .expect("latest op")
            .approval_state
            .state = String::new();

        let lease =
            DispatchLease::new(12, "op-1", Some(DispatchLane::Heavy), 10, 500, "cp-lease-1");

        let projection = build_task_projection(&task, Some(&lease));

        assert_eq!(projection.runtime_state, "in_flight");
        assert!(projection.in_flight_lock);
        assert_eq!(projection.lease_expires_at_ms, Some(510));
        assert_eq!(projection.correlation_id.as_deref(), Some("cp-lease-1"));
    }

    #[test]
    fn task_projection_surfaces_failure_reason() {
        let mut task = sample_task();
        let latest_operation = task.latest_operation.as_mut().expect("latest op");
        latest_operation.status = "failed".to_string();
        latest_operation.approval_state.state = String::new();
        latest_operation.session_projection.latest_event_message =
            Some("训练任务因样本不足失败".to_string());

        let projection = build_task_projection(&task, None);

        assert_eq!(projection.runtime_state, "attention_required");
        assert_eq!(
            projection.last_failure_reason.as_deref(),
            Some("训练任务因样本不足失败")
        );
    }

    #[test]
    fn decode_control_task_records_accepts_nested_control_tasks_shape() {
        let payload = serde_json::json!({
            "success": true,
            "data": {
                "control_tasks": [
                    {
                        "id": "fetch_data_hourly",
                        "kind": "scheduler",
                        "operation_type": "fetch_data",
                        "title": "每小时外部数据抓取",
                        "enabled": true,
                        "dependency_state": "none",
                        "dependency_summary": "无依赖",
                        "dependencies": [],
                        "dependency_details": [],
                        "approval_policy": {},
                        "default_input": {},
                        "latest_operation": null
                    }
                ]
            }
        });

        let records = decode_control_task_records(&payload).expect("records should decode");
        assert_eq!(records.len(), 1);
        assert_eq!(records[0].id, "fetch_data_hourly");
    }
}
