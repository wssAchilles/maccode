use std::{net::SocketAddr, sync::Arc};

use anyhow::{Context, Result};
use reqwest::Client;

use crate::controller::DispatchController;

#[derive(Debug, Clone)]
pub struct AppConfig {
    pub host: String,
    pub port: u16,
    pub python_worker_base_url: Option<String>,
    pub internal_job_token: String,
    pub max_light_parallel: usize,
    pub max_heavy_parallel: usize,
    pub dispatch_timeout_secs: u64,
}

impl AppConfig {
    pub fn from_env() -> Self {
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
            max_light_parallel: std::env::var("MAX_LIGHT_PARALLEL")
                .ok()
                .and_then(|value| value.parse().ok())
                .unwrap_or(4),
            max_heavy_parallel: std::env::var("MAX_HEAVY_PARALLEL")
                .ok()
                .and_then(|value| value.parse().ok())
                .unwrap_or(2),
            dispatch_timeout_secs: std::env::var("DISPATCH_TIMEOUT_SECS")
                .ok()
                .and_then(|value| value.parse().ok())
                .unwrap_or(1800),
        }
    }

    pub fn bind_addr(&self) -> Result<SocketAddr> {
        format!("{}:{}", self.host, self.port)
            .parse()
            .context("invalid HOST or PORT")
    }
}

#[derive(Clone)]
pub struct AppState {
    pub config: Arc<AppConfig>,
    pub http_client: Client,
    pub dispatch_controller: DispatchController,
}
