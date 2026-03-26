mod context;
mod payload;
mod reasons;

use axum::http::StatusCode;

use crate::gateway_types::{AppState, GatewayMetrics};

use context::build_readiness_context;
use payload::build_readiness_payload;
use reasons::collect_readiness_reasons;

pub(super) fn build_ready_payload(
    state: &AppState,
    metrics: &GatewayMetrics,
) -> (StatusCode, serde_json::Value) {
    let context = build_readiness_context(state, metrics);
    let reasons = collect_readiness_reasons(state, metrics, &context);
    let ready = reasons.is_empty();
    let status = if ready {
        StatusCode::OK
    } else {
        StatusCode::SERVICE_UNAVAILABLE
    };

    (
        status,
        build_readiness_payload(state, metrics, &context, reasons, ready),
    )
}
