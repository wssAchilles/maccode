use axum::{
    Json,
    extract::{Path, State},
    http::StatusCode,
    response::Response,
};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

use crate::{
    config::AppState,
    proxy::{proxy_empty_post, proxy_get, proxy_json_patch, proxy_json_post, proxy_sse_get},
};

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

pub async fn healthz(State(state): State<AppState>) -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok",
        service: "sentinel-orchestrator",
        python_worker_configured: state.config.python_worker_base_url.is_some(),
    })
}

pub async fn dispatch_operation(
    State(state): State<AppState>,
    Path(operation_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    proxy_empty_post(
        &state,
        format!("/internal/operations/{operation_id}/dispatch"),
    )
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
    proxy_empty_post(&state, format!("/internal/operations/{operation_id}/retry")).await
}

pub async fn approve_operation(
    State(state): State<AppState>,
    Path(operation_id): Path<String>,
    Json(payload): Json<ApprovalRequest>,
) -> (StatusCode, Json<Value>) {
    proxy_json_post(
        &state,
        format!("/internal/operations/{operation_id}/approve"),
        json!({
            "approved": payload.approved,
            "message": payload.message,
        }),
    )
    .await
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
