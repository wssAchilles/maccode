use std::{net::SocketAddr, sync::Arc};

use anyhow::{Context, Result};
use axum::{
    extract::{Path, State},
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tower_http::{cors::CorsLayer, trace::TraceLayer};
use tracing::{info, warn};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

#[derive(Debug, Clone)]
struct AppConfig {
    host: String,
    port: u16,
    python_worker_base_url: Option<String>,
    internal_job_token: String,
}

impl AppConfig {
    fn from_env() -> Self {
        Self {
            host: std::env::var("HOST").unwrap_or_else(|_| "0.0.0.0".to_string()),
            port: std::env::var("PORT")
                .ok()
                .and_then(|value| value.parse().ok())
                .unwrap_or(8080),
            python_worker_base_url: std::env::var("PYTHON_WORKER_BASE_URL")
                .ok()
                .map(|value| value.trim_end_matches('/').to_string())
                .filter(|value| !value.is_empty()),
            internal_job_token: std::env::var("INTERNAL_JOB_TOKEN")
                .unwrap_or_else(|_| "dev-internal-job-token".to_string()),
        }
    }

    fn bind_addr(&self) -> Result<SocketAddr> {
        format!("{}:{}", self.host, self.port)
            .parse()
            .context("invalid HOST or PORT")
    }
}

#[derive(Clone)]
struct AppState {
    config: Arc<AppConfig>,
    http_client: Client,
}

#[derive(Debug, Deserialize)]
struct ApprovalRequest {
    approved: bool,
    message: Option<String>,
}

#[derive(Debug, Serialize)]
struct HealthResponse {
    status: &'static str,
    service: &'static str,
    python_worker_configured: bool,
}

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
        config,
        http_client: Client::builder()
            .use_rustls_tls()
            .build()
            .context("failed to build reqwest client")?,
    };

    let app = Router::new()
        .route("/healthz", get(healthz))
        .route("/internal/operations/{operation_id}/dispatch", post(dispatch_operation))
        .route("/internal/operations/{operation_id}/cancel", post(cancel_operation))
        .route("/internal/operations/{operation_id}/retry", post(retry_operation))
        .route("/internal/operations/{operation_id}/approve", post(approve_operation))
        .route("/internal/operations/{operation_id}", get(get_operation))
        .route("/internal/operations/{operation_id}/events", get(get_operation_events))
        .with_state(state)
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http());

    let listener = tokio::net::TcpListener::bind(bind_addr)
        .await
        .context("failed to bind sentinel orchestrator")?;
    info!("sentinel orchestrator listening on {}", listener.local_addr()?);

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .context("sentinel orchestrator server failed")?;

    Ok(())
}

async fn healthz(State(state): State<AppState>) -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok",
        service: "sentinel-orchestrator",
        python_worker_configured: state.config.python_worker_base_url.is_some(),
    })
}

async fn dispatch_operation(
    State(state): State<AppState>,
    Path(operation_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    proxy_empty_post(&state, format!("/internal/operations/{operation_id}/dispatch")).await
}

async fn cancel_operation(
    State(state): State<AppState>,
    Path(operation_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    proxy_empty_post(&state, format!("/internal/operations/{operation_id}/cancel")).await
}

async fn retry_operation(
    State(state): State<AppState>,
    Path(operation_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    proxy_empty_post(&state, format!("/internal/operations/{operation_id}/retry")).await
}

async fn approve_operation(
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

async fn get_operation(
    State(state): State<AppState>,
    Path(operation_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    proxy_get(&state, format!("/internal/operations/{operation_id}")).await
}

async fn get_operation_events(
    State(state): State<AppState>,
    Path(operation_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    proxy_get(&state, format!("/internal/operations/{operation_id}/events")).await
}

async fn proxy_empty_post(state: &AppState, path: String) -> (StatusCode, Json<Value>) {
    proxy_request(state, reqwest::Method::POST, path, None).await
}

async fn proxy_json_post(
    state: &AppState,
    path: String,
    payload: Value,
) -> (StatusCode, Json<Value>) {
    proxy_request(state, reqwest::Method::POST, path, Some(payload)).await
}

async fn proxy_get(state: &AppState, path: String) -> (StatusCode, Json<Value>) {
    proxy_request(state, reqwest::Method::GET, path, None).await
}

async fn proxy_request(
    state: &AppState,
    method: reqwest::Method,
    path: String,
    payload: Option<Value>,
) -> (StatusCode, Json<Value>) {
    let Some(base_url) = state.config.python_worker_base_url.as_ref() else {
        warn!("python worker base url not configured for {}", path);
        return (
            StatusCode::SERVICE_UNAVAILABLE,
            Json(json!({
                "success": false,
                "error": {
                    "code": "PYTHON_WORKER_UNAVAILABLE",
                    "message": "PYTHON_WORKER_BASE_URL is not configured",
                }
            })),
        );
    };

    let url = format!("{base_url}{path}");
    let mut request = state
        .http_client
        .request(method, &url)
        .header("Content-Type", "application/json")
        .header("X-Internal-Job-Token", &state.config.internal_job_token);

    if let Some(body) = payload {
        request = request.json(&body);
    }

    match request.send().await {
        Ok(response) => {
            let status = response.status();
            match response.json::<Value>().await {
                Ok(body) => (status, Json(body)),
                Err(error) => {
                    warn!("failed to decode response from {}: {}", url, error);
                    (
                        StatusCode::BAD_GATEWAY,
                        Json(json!({
                            "success": false,
                            "error": {
                                "code": "UPSTREAM_BAD_RESPONSE",
                                "message": format!("Failed to decode upstream response from {url}"),
                            }
                        })),
                    )
                }
            }
        }
        Err(error) => {
            warn!("failed to contact {}: {}", url, error);
            (
                StatusCode::BAD_GATEWAY,
                Json(json!({
                    "success": false,
                    "error": {
                        "code": "UPSTREAM_UNAVAILABLE",
                        "message": format!("Failed to reach python worker at {url}"),
                    }
                })),
            )
        }
    }
}

async fn shutdown_signal() {
    let ctrl_c = async {
        let _ = tokio::signal::ctrl_c().await;
    };

    #[cfg(unix)]
    let terminate = async {
        use tokio::signal::unix::{signal, SignalKind};

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
