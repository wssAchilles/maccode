use axum::{
    extract::{Extension, Path, State},
    http::StatusCode,
    Json,
};

use crate::gateway_types::{
    AppState, RequestContext, StrategyOrchestrationEntryUpdateRequest,
    StrategyOrchestrationPolicyUpdateRequest, REQUEST_ID_HEADER,
};
use crate::handlers::common::{error_body, with_request_context};
use crate::handlers::trading::strategy::upstream::send_strategy_request;

pub(crate) async fn get_strategy_orchestration_status(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    proxy_strategy_json(
        &state,
        &ctx,
        "/api/v1/strategy/orchestration/status",
        state
            .http_client
            .get(strategy_url(&state, "/api/v1/strategy/orchestration/status")?)
            .header(REQUEST_ID_HEADER, ctx.request_id.as_str()),
    )
    .await
}

pub(crate) async fn update_strategy_orchestration_entry(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
    Path(strategy_id): Path<String>,
    Json(body): Json<StrategyOrchestrationEntryUpdateRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let path = format!("/api/v1/strategy/orchestration/entries/{strategy_id}");
    proxy_strategy_json(
        &state,
        &ctx,
        path.as_str(),
        state
            .http_client
            .post(strategy_url(&state, path.as_str())?)
            .header(REQUEST_ID_HEADER, ctx.request_id.as_str())
            .json(&body),
    )
    .await
}

pub(crate) async fn update_strategy_orchestration_policies(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
    Json(body): Json<StrategyOrchestrationPolicyUpdateRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    proxy_strategy_json(
        &state,
        &ctx,
        "/api/v1/strategy/orchestration/policies",
        state
            .http_client
            .post(strategy_url(&state, "/api/v1/strategy/orchestration/policies")?)
            .header(REQUEST_ID_HEADER, ctx.request_id.as_str())
            .json(&body),
    )
    .await
}

async fn proxy_strategy_json(
    state: &AppState,
    ctx: &RequestContext,
    path: &str,
    request: reqwest::RequestBuilder,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let response = send_strategy_request(state, request, state.strategy_upstream.timeout_ms)
        .await
        .map_err(|err| {
            (
                StatusCode::BAD_GATEWAY,
                error_body(
                    "strategy_upstream_error",
                    format!("{path} failed: {}", err.client_message()),
                    ctx.request_id.as_str(),
                ),
            )
        })?;

    let status = response.status();
    let body = response
        .json::<serde_json::Value>()
        .await
        .unwrap_or_else(|_| serde_json::json!({}));

    if !status.is_success() {
        return Err((
            status,
            error_body(
                "strategy_request_failed",
                body.get("detail")
                    .map(std::string::ToString::to_string)
                    .unwrap_or_else(|| format!("{path} failed")),
                ctx.request_id.as_str(),
            ),
        ));
    }

    Ok(Json(with_request_context(
        body,
        ctx.request_id.as_str(),
        ctx.idempotency_key.as_deref(),
    )))
}

fn strategy_url(state: &AppState, path: &str) -> Result<String, (StatusCode, Json<serde_json::Value>)> {
    let strategy_base = state.strategy_base_url.as_ref().ok_or((
        StatusCode::SERVICE_UNAVAILABLE,
        error_body("config_error", "STRATEGY_BASE_URL not configured", "gateway"),
    ))?;
    Ok(format!("{}{}", strategy_base.trim_end_matches('/'), path))
}
