use axum::{
    Json,
    extract::{Path, Query, State},
    http::{HeaderMap, StatusCode},
    response::Response,
};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::HashMap;

use crate::telemetry::{ComputeRolloutTelemetry, fetch_compute_rollout};
use crate::{
    config::AppState,
    connector::{ConnectorDegradedMode, ConnectorHealthcheck, build_connector_lifecycle},
    contract::ControlPlaneActionResponse,
    models::OperationEnvelope,
    policy::{
        CONTROL_PLANE_POLICY_VERSION, OperationSnapshot, evaluate_approval_decision,
        evaluate_cancel_decision, evaluate_retry_decision,
    },
    proxy::{
        proxy_empty_post, proxy_get, proxy_json_patch, proxy_json_post,
        proxy_json_post_with_headers, proxy_sse_get,
    },
    runtime_projection::get_runtime_projection,
    telemetry::{ComputeAccelerationTelemetry, fetch_compute_acceleration},
    upstream::{UpstreamFailureRecord, UpstreamReachability, WorkerHealthSnapshot},
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

#[derive(Debug, Deserialize)]
pub struct RuntimeSnapshotQuery {
    pub uid: Option<String>,
    pub fresh: Option<String>,
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
    pub policy_version: &'static str,
    pub python_worker_configured: bool,
    pub active_operations: usize,
    pub dispatch_timeout_secs: u64,
    pub light_lane: ControlPlaneLaneStatus,
    pub heavy_lane: ControlPlaneLaneStatus,
    pub upstream_reachability: UpstreamReachability,
    pub last_upstream_error: Option<UpstreamFailureRecord>,
    pub last_successful_contact_at_ms: Option<u64>,
    pub degraded: bool,
    pub degraded_components: Vec<String>,
    pub worker_health: Vec<WorkerHealthSnapshot>,
    pub connectors: Vec<ConnectorHealthcheck>,
    pub degraded_mode: Option<ConnectorDegradedMode>,
    pub last_correlation_id: Option<String>,
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
    let worker_health_summary = state
        .worker_health_registry
        .summary(&state.config.worker_configs())
        .await;
    let connector_lifecycle =
        build_connector_lifecycle(&state.config.worker_configs(), &worker_health_summary);
    Json(ControlPlaneStatusResponse {
        status: "ok",
        service: "sentinel-orchestrator",
        policy_version: CONTROL_PLANE_POLICY_VERSION,
        python_worker_configured: state.config.python_worker_base_url.is_some(),
        active_operations: snapshot.active_operations,
        dispatch_timeout_secs: snapshot.dispatch_timeout_secs,
        light_lane: ControlPlaneLaneStatus {
            capacity: snapshot.light_capacity,
            available: snapshot.light_available,
            in_use: snapshot
                .light_capacity
                .saturating_sub(snapshot.light_available),
        },
        heavy_lane: ControlPlaneLaneStatus {
            capacity: snapshot.heavy_capacity,
            available: snapshot.heavy_available,
            in_use: snapshot
                .heavy_capacity
                .saturating_sub(snapshot.heavy_available),
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
        compute_acceleration,
        compute_rollout,
    })
}

pub async fn dispatch_operation(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(operation_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    let correlation_id = state.correlation_ids.resolve_or_generate(&headers);
    state
        .dispatch_controller
        .enqueue_dispatch(state.clone(), operation_id, correlation_id)
        .await
}

pub async fn cancel_operation(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(operation_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    let correlation_id = state.correlation_ids.resolve_or_generate(&headers);
    let response = proxy_empty_post(
        &state,
        format!("/internal/operations/{operation_id}/cancel"),
        Some(&correlation_id),
    )
    .await;
    if let Some(operation) = extract_operation_snapshot(&response) {
        let decision = evaluate_cancel_decision(&operation);
        let body = serde_json::to_value(ControlPlaneActionResponse::from_cancel_decision(
            &decision,
            &correlation_id,
            operation.status == "queued",
        ))
        .unwrap_or_else(|_| json!({}));
        return (response.0, Json(body));
    }
    upstream_error_response(response, &operation_id, &correlation_id)
}

pub async fn retry_operation(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(operation_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    let correlation_id = state.correlation_ids.resolve_or_generate(&headers);
    let mut headers = HashMap::new();
    headers.insert("X-Orchestrator-Managed".to_string(), "true".to_string());
    let response = proxy_json_post_with_headers(
        &state,
        format!("/internal/operations/{operation_id}/retry"),
        json!({}),
        headers,
        Some(&correlation_id),
    )
    .await;
    if let Some(operation) = extract_operation_snapshot(&response) {
        let decision = evaluate_retry_decision(&operation);
        queue_dispatch_for_followup(
            &state,
            &operation_id,
            decision.should_enqueue_dispatch,
            &correlation_id,
        )
        .await;
        let body = serde_json::to_value(ControlPlaneActionResponse::from_retry_decision(
            &decision,
            &correlation_id,
            operation.status == "queued",
        ))
        .unwrap_or_else(|_| json!({}));
        return (response.0, Json(body));
    }
    upstream_error_response(response, &operation_id, &correlation_id)
}

pub async fn approve_operation(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(operation_id): Path<String>,
    Json(payload): Json<ApprovalRequest>,
) -> (StatusCode, Json<Value>) {
    let correlation_id = state.correlation_ids.resolve_or_generate(&headers);
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
        Some(&correlation_id),
    )
    .await;
    if let Some(operation) = extract_operation_snapshot(&response) {
        let decision = evaluate_approval_decision(&operation, payload.approved);
        if payload.approved {
            queue_dispatch_for_followup(
                &state,
                &operation_id,
                decision.should_enqueue_dispatch,
                &correlation_id,
            )
            .await;
        }
        let body = serde_json::to_value(ControlPlaneActionResponse::from_approval_decision(
            &decision,
            &correlation_id,
            operation.status == "queued",
        ))
        .unwrap_or_else(|_| json!({}));
        return (response.0, Json(body));
    }
    upstream_error_response(response, &operation_id, &correlation_id)
}

pub async fn get_operation(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(operation_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    let correlation_id = state.correlation_ids.resolve_or_generate(&headers);
    proxy_get(
        &state,
        format!("/internal/operations/{operation_id}"),
        Some(&correlation_id),
    )
    .await
}

pub async fn get_operation_events(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(operation_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    let correlation_id = state.correlation_ids.resolve_or_generate(&headers);
    proxy_get(
        &state,
        format!("/internal/operations/{operation_id}/events"),
        Some(&correlation_id),
    )
    .await
}

pub async fn stream_operation(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(operation_id): Path<String>,
) -> Response {
    let correlation_id = state.correlation_ids.resolve_or_generate(&headers);
    proxy_sse_get(
        &state,
        format!("/internal/operations/{operation_id}/stream"),
        operation_id,
        correlation_id,
    )
    .await
}

pub async fn run_control_task(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(control_task_id): Path<String>,
    Json(payload): Json<RunControlTaskRequest>,
) -> (StatusCode, Json<Value>) {
    let correlation_id = state.correlation_ids.resolve_or_generate(&headers);
    proxy_json_post(
        &state,
        format!("/internal/control-tasks/{control_task_id}/run"),
        json!({
            "requested_by": payload.requested_by,
            "input": payload.input,
            "trigger": payload.trigger,
        }),
        Some(&correlation_id),
    )
    .await
}

pub async fn list_control_tasks(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> (StatusCode, Json<Value>) {
    let correlation_id = state.correlation_ids.resolve_or_generate(&headers);
    proxy_get(
        &state,
        "/internal/control-tasks".to_string(),
        Some(&correlation_id),
    )
    .await
}

pub async fn get_control_task(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(control_task_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    let correlation_id = state.correlation_ids.resolve_or_generate(&headers);
    proxy_get(
        &state,
        format!("/internal/control-tasks/{control_task_id}"),
        Some(&correlation_id),
    )
    .await
}

pub async fn update_control_task(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(control_task_id): Path<String>,
    Json(payload): Json<UpdateControlTaskRequest>,
) -> (StatusCode, Json<Value>) {
    let correlation_id = state.correlation_ids.resolve_or_generate(&headers);
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
        Some(&correlation_id),
    )
    .await
}

pub async fn get_runtime_snapshot(
    State(state): State<AppState>,
    Query(query): Query<RuntimeSnapshotQuery>,
) -> (StatusCode, Json<Value>) {
    let force_refresh = query
        .fresh
        .as_deref()
        .is_some_and(|value| matches!(value.to_ascii_lowercase().as_str(), "1" | "true" | "yes"));
    let uid = query.uid.as_deref().unwrap_or("system");
    let snapshot = get_runtime_projection(&state, uid, force_refresh).await;
    (
        StatusCode::OK,
        Json(serde_json::to_value(snapshot).unwrap_or_else(|_| json!({}))),
    )
}

fn extract_operation_snapshot(response: &(StatusCode, Json<Value>)) -> Option<OperationSnapshot> {
    if !response.0.is_success() {
        return None;
    }

    serde_json::from_value::<OperationEnvelope<OperationSnapshot>>(response.1.0.clone())
        .ok()
        .map(|envelope| envelope.data)
}

async fn queue_dispatch_for_followup(
    state: &AppState,
    operation_id: &str,
    should_enqueue_dispatch: bool,
    correlation_id: &str,
) {
    if !should_enqueue_dispatch {
        return;
    }

    let _ = state
        .dispatch_controller
        .enqueue_dispatch(
            state.clone(),
            operation_id.to_string(),
            correlation_id.to_string(),
        )
        .await;
}

fn upstream_error_response(
    response: (StatusCode, Json<Value>),
    operation_id: &str,
    correlation_id: &str,
) -> (StatusCode, Json<Value>) {
    let body = serde_json::to_value(ControlPlaneActionResponse::upstream_error(
        operation_id.to_string(),
        correlation_id,
        extract_upstream_error_message(&response.1.0),
        response.1.0,
    ))
    .unwrap_or_else(|_| json!({}));
    (response.0, Json(body))
}

fn extract_upstream_error_message(payload: &Value) -> String {
    payload
        .get("error")
        .and_then(|error| error.get("message"))
        .and_then(Value::as_str)
        .filter(|message| !message.is_empty())
        .unwrap_or("Control-plane upstream request failed")
        .to_string()
}
