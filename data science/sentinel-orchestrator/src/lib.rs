pub mod auth;
pub mod config;
pub mod connector;
pub mod contract;
pub mod controller;
pub mod correlation;
pub mod handlers;
pub mod models;
pub mod policy;
pub mod proxy;
pub mod runtime_projection;
pub mod telemetry;
pub mod upstream;

use std::sync::Arc;

use anyhow::{Context, Result};
use axum::{
    Router, middleware,
    routing::{get, post},
};
use controller::DispatchController;
use correlation::CorrelationIdGenerator;
use handlers::{
    approve_operation, cancel_operation, dispatch_operation, get_control_task, get_operation,
    get_operation_events, get_runtime_snapshot, healthz, list_control_tasks, retry_operation,
    run_control_task, statusz, stream_operation, update_control_task,
};
use reqwest::Client;
use runtime_projection::RuntimeProjectionCache;
use tower_http::{cors::CorsLayer, trace::TraceLayer};
use upstream::WorkerHealthRegistry;

pub use config::{AppConfig, AppState};

pub fn build_state(config: Arc<AppConfig>) -> Result<AppState> {
    Ok(AppState {
        dispatch_controller: DispatchController::new(
            config.max_light_parallel,
            config.max_heavy_parallel,
            std::time::Duration::from_secs(config.dispatch_timeout_secs),
        ),
        config,
        http_client: Client::builder()
            .use_rustls_tls()
            .build()
            .context("failed to build reqwest client")?,
        worker_health_registry: WorkerHealthRegistry::new(),
        correlation_ids: CorrelationIdGenerator::default(),
        runtime_projection_cache: RuntimeProjectionCache::default(),
    })
}

#[must_use]
pub fn build_app(state: AppState) -> Router {
    let internal_routes = Router::new()
        .route(
            "/internal/operations/{operation_id}/dispatch",
            post(dispatch_operation),
        )
        .route(
            "/internal/operations/{operation_id}/cancel",
            post(cancel_operation),
        )
        .route(
            "/internal/operations/{operation_id}/retry",
            post(retry_operation),
        )
        .route(
            "/internal/operations/{operation_id}/approve",
            post(approve_operation),
        )
        .route("/internal/operations/{operation_id}", get(get_operation))
        .route(
            "/internal/operations/{operation_id}/events",
            get(get_operation_events),
        )
        .route(
            "/internal/operations/{operation_id}/stream",
            get(stream_operation),
        )
        .route("/internal/control-tasks", get(list_control_tasks))
        .route(
            "/internal/control-tasks/{control_task_id}",
            get(get_control_task).patch(update_control_task),
        )
        .route(
            "/internal/control-tasks/{control_task_id}/run",
            post(run_control_task),
        )
        .route("/internal/runtime/snapshot", get(get_runtime_snapshot))
        .layer(middleware::from_fn_with_state(
            state.clone(),
            auth::require_internal_token,
        ));

    Router::new()
        .route("/healthz", get(healthz))
        .route("/readyz", get(statusz))
        .route("/statusz", get(statusz))
        .merge(internal_routes)
        .with_state(state)
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http())
}
