mod config;
mod controller;
mod handlers;
mod models;
mod proxy;

use anyhow::{Context, Result};
use axum::{
    Router,
    routing::{get, post},
};
use config::{AppConfig, AppState};
use controller::DispatchController;
use handlers::{
    approve_operation, cancel_operation, dispatch_operation, get_control_task, get_operation,
    get_operation_events, healthz, list_control_tasks, retry_operation, run_control_task,
    stream_operation, update_control_task,
};
use reqwest::Client;
use std::sync::Arc;
use tower_http::{cors::CorsLayer, trace::TraceLayer};
use tracing::info;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "sentinel_orchestrator=info,tower_http=info".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();

    let config = Arc::new(AppConfig::from_env());
    let bind_addr = config.bind_addr()?;
    let state = AppState {
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
    };

    let app = Router::new()
        .route("/healthz", get(healthz))
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
        .with_state(state)
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http());

    let listener = tokio::net::TcpListener::bind(bind_addr)
        .await
        .context("failed to bind sentinel orchestrator")?;
    info!(
        "sentinel orchestrator listening on {}",
        listener.local_addr()?
    );

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .context("sentinel orchestrator server failed")?;

    Ok(())
}

async fn shutdown_signal() {
    let ctrl_c = async {
        let _ = tokio::signal::ctrl_c().await;
    };

    #[cfg(unix)]
    let terminate = async {
        use tokio::signal::unix::{SignalKind, signal};

        match signal(SignalKind::terminate()) {
            Ok(mut signal) => {
                signal.recv().await;
            }
            Err(_) => std::future::pending::<()>().await,
        }
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {}
        _ = terminate => {}
    }
}
