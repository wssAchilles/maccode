use std::net::SocketAddr;

use anyhow::Context;
use tracing::info;

mod bootstrap;
mod event_bus;
mod gateway_types;
mod gateway_utils;
mod handlers;
mod ingest;
mod ws;

use bootstrap::{
    build_router, build_state_from_env, load_bootstrap_runtime, validate_runtime_policies,
};
use ingest::{spawn_market_ingest, spawn_order_events_ingest};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    init_tracing();

    let runtime = load_bootstrap_runtime();
    let state = build_state_from_env(&runtime);
    validate_runtime_policies(&state)?;

    spawn_market_ingest(state.clone());
    spawn_order_events_ingest(state.clone());

    let app = build_router(state, runtime.cors_allow_origins.as_str());
    let addr = build_bind_addr(runtime.port.as_str())?;

    info!("gateway listening on {addr}");

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

fn init_tracing() {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();
}

fn build_bind_addr(port: &str) -> anyhow::Result<SocketAddr> {
    format!("0.0.0.0:{port}")
        .parse()
        .context("invalid bind address")
}
