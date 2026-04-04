use axum::{
    Json,
    extract::{Path, State},
    http::StatusCode,
    response::Response,
};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::HashMap;

use crate::{
    config::AppState,
    proxy::{
        proxy_empty_post, proxy_get, proxy_json_patch, proxy_json_post,
        proxy_json_post_with_headers, proxy_sse_get,
    },
    telemetry::{ComputeAccelerationTelemetry, fetch_compute_acceleration},
};
use crate::telemetry::{ComputeRolloutTelemetry, fetch_compute_rollout};

#[derive(Debug, Deserialize)]
pub struct ApprovalRequest {
    pub approved: bool,
    pub message: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct RunControlTaskRequest {
    pub requested_by: Option<String>,
    pub input: Option<Value>,
    pub trigger: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateControlTaskRequest {
    pub enabled: Option<bool>,
    pub approval_policy: Option<Value>,
    pub dependencies: Option<Vec<String>>,
    pub schedule: Option<String>,
    pub owner: Option<String>,
    pub default_input: Option<Value>,
}

#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: &'static str,
    pub service: &'static str,
    pub python_worker_configured: bool,
}

#[derive(Debug, Serialize)]
pub struct ControlPlaneStatusResponse {
    pub status: &'static str,
    pub service: &'static str,
    pub python_worker_configured: bool,
    pub active_operations: usize,
    pub dispatch_timeout_secs: u64,
    pub light_lane: ControlPlaneLaneStatus,
    pub heavy_lane: ControlPlaneLaneStatus,
    pub compute_acceleration: ComputeAccelerationTelemetry,
    pub compute_rollout: ComputeRolloutTelemetry,
}

#[derive(Debug, Serialize)]
pub struct ControlPlaneLaneStatus {
    pub capacity: usize,
    pub available: usize,
    pub in_use: usize,
}

pub async fn healthz(State(state): State<AppState>) -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok",
        service: "sentinel-orchestrator",
        python_worker_configured: state.config.python_worker_base_url.is_some(),
    })
}

pub async fn statusz(State(state): State<AppState>) -> Json<ControlPlaneStatusResponse> {
    let snapshot = state.dispatch_controller.snapshot().await;
    let compute_acceleration = fetch_compute_acceleration(&state).await;
    let compute_rollout = fetch_compute_rollout(&state).await;
    Json(ControlPlaneStatusResponse {
        status: "ok",
        service: "sentinel-orchestrator",
        python_worker_configured: state.config.python_worker_base_url.is_some(),
        active_operations: snapshot.active_operations,
        dispatch_timeout_secs: snapshot.dispatch_timeout_secs,
        light_lane: ControlPlaneLaneStatus {
            capacity: snapshot.light_capacity,
            available: snapshot.light_available,
            in_use: snapshot.light_capacity.saturating_sub(snapshot.light_available),
        },
        heavy_lane: ControlPlaneLaneStatus {
            capacity: snapshot.heavy_capacity,
            available: snapshot.heavy_available,
            in_use: snapshot.heavy_capacity.saturating_sub(snapshot.heavy_available),
        },
        compute_acceleration,
        compute_rollout,
    })
}

pub async fn dispatch_operation(
    State(state): State<AppState>,
    Path(operation_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    state
        .dispatch_controller
        .enqueue_dispatch(state.clone(), operation_id)
        .await
}

pub async fn cancel_operation(
    State(state): State<AppState>,
    Path(operation_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    proxy_empty_post(
        &state,
        format!("/internal/operations/{operation_id}/cancel"),
    )
    .await
}

pub async fn retry_operation(
    State(state): State<AppState>,
    Path(operation_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    let mut headers = HashMap::new();
    headers.insert("X-Orchestrator-Managed".to_string(), "true".to_string());
    let response = proxy_json_post_with_headers(
        &state,
        format!("/internal/operations/{operation_id}/retry"),
        json!({}),
        headers,
    )
    .await;
    queue_dispatch_if_needed(&state, &operation_id, &response).await;
    response
}

pub async fn approve_operation(
    State(state): State<AppState>,
    Path(operation_id): Path<String>,
    Json(payload): Json<ApprovalRequest>,
) -> (StatusCode, Json<Value>) {
    let mut headers = HashMap::new();
    headers.insert("X-Orchestrator-Managed".to_string(), "true".to_string());
    let response = proxy_json_post_with_headers(
        &state,
        format!("/internal/operations/{operation_id}/approve"),
        json!({
            "approved": payload.approved,
            "message": payload.message,
        }),
        headers,
    )
    .await;
    if payload.approved {
        queue_dispatch_if_needed(&state, &operation_id, &response).await;
    }
    response
}

pub async fn get_operation(
    State(state): State<AppState>,
    Path(operation_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    proxy_get(&state, format!("/internal/operations/{operation_id}")).await
}

pub async fn get_operation_events(
    State(state): State<AppState>,
    Path(operation_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    proxy_get(
        &state,
        format!("/internal/operations/{operation_id}/events"),
    )
    .await
}

pub async fn stream_operation(
    State(state): State<AppState>,
    Path(operation_id): Path<String>,
) -> Response {
    proxy_sse_get(
        &state,
        format!("/internal/operations/{operation_id}/stream"),
    )
    .await
}

pub async fn run_control_task(
    State(state): State<AppState>,
    Path(control_task_id): Path<String>,
    Json(payload): Json<RunControlTaskRequest>,
) -> (StatusCode, Json<Value>) {
    proxy_json_post(
        &state,
        format!("/internal/control-tasks/{control_task_id}/run"),
        json!({
            "requested_by": payload.requested_by,
            "input": payload.input,
            "trigger": payload.trigger,
        }),
    )
    .await
}

pub async fn list_control_tasks(State(state): State<AppState>) -> (StatusCode, Json<Value>) {
    proxy_get(&state, "/internal/control-tasks".to_string()).await
}

pub async fn get_control_task(
    State(state): State<AppState>,
    Path(control_task_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    proxy_get(&state, format!("/internal/control-tasks/{control_task_id}")).await
}

pub async fn update_control_task(
    State(state): State<AppState>,
    Path(control_task_id): Path<String>,
    Json(payload): Json<UpdateControlTaskRequest>,
) -> (StatusCode, Json<Value>) {
    proxy_json_patch(
        &state,
        format!("/internal/control-tasks/{control_task_id}"),
        json!({
            "enabled": payload.enabled,
            "approval_policy": payload.approval_policy,
            "dependencies": payload.dependencies,
            "schedule": payload.schedule,
            "owner": payload.owner,
            "default_input": payload.default_input,
        }),
    )
    .await
}

async fn queue_dispatch_if_needed(
    state: &AppState,
    operation_id: &str,
    response: &(StatusCode, Json<Value>),
) {
    if !response.0.is_success() {
        return;
    }

    let Some(status) = response
        .1
        .0
        .get("data")
        .and_then(|data| data.get("status"))
        .and_then(Value::as_str)
    else {
        return;
    };

    if status != "queued" {
        return;
    }

    let _ = state
        .dispatch_controller
        .enqueue_dispatch(state.clone(), operation_id.to_string())
        .await;
}
