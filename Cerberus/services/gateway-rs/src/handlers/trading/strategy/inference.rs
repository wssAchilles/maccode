use axum::{
    extract::{Extension, State},
    http::StatusCode,
    Json,
};

use crate::gateway_types::{
    AppState, InferenceActionRequest, InferenceActivateModelRequest, RequestContext,
    REQUEST_ID_HEADER,
};
use crate::gateway_utils::to_axum_status;
use crate::handlers::common::{error_body, error_body_value, with_request_context};
use crate::handlers::trading::strategy::upstream::send_strategy_request;
use super::summary::downstream_errors::normalize_downstream_error;

pub(crate) async fn get_inference_models(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    proxy_strategy_json(
        &state,
        &ctx,
        "/api/v1/inference/models",
        state
            .http_client
            .get(strategy_url(&state, "/api/v1/inference/models")?)
            .header(REQUEST_ID_HEADER, ctx.request_id.as_str()),
    )
    .await
}

pub(crate) async fn promote_inference_rollout(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
    Json(body): Json<InferenceActionRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    proxy_strategy_json(
        &state,
        &ctx,
        "/api/v1/inference/rollout/promote",
        state
            .http_client
            .post(strategy_url(&state, "/api/v1/inference/rollout/promote")?)
            .header(REQUEST_ID_HEADER, ctx.request_id.as_str())
            .json(&body),
    )
    .await
}

pub(crate) async fn rollback_inference_rollout(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
    Json(body): Json<InferenceActionRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    proxy_strategy_json(
        &state,
        &ctx,
        "/api/v1/inference/rollout/rollback",
        state
            .http_client
            .post(strategy_url(&state, "/api/v1/inference/rollout/rollback")?)
            .header(REQUEST_ID_HEADER, ctx.request_id.as_str())
            .json(&body),
    )
    .await
}

pub(crate) async fn activate_inference_model(
    State(state): State<AppState>,
    Extension(ctx): Extension<RequestContext>,
    Json(body): Json<InferenceActivateModelRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    proxy_strategy_json(
        &state,
        &ctx,
        "/api/v1/inference/models/activate",
        state
            .http_client
            .post(strategy_url(&state, "/api/v1/inference/models/activate")?)
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
    let status = to_axum_status(status);
    let body = response
        .json::<serde_json::Value>()
        .await
        .unwrap_or_else(|_| serde_json::json!({}));

    if !status.is_success() {
        let error_payload = normalize_downstream_error(&body, status, ctx.request_id.as_str());
        return Err((
            status,
            error_body_value(error_payload, ctx.request_id.as_str()),
        ));
    }

    Ok(Json(with_request_context(
        body,
        ctx.request_id.as_str(),
        ctx.idempotency_key.as_deref(),
    )))
}

fn strategy_url(
    state: &AppState,
    path: &str,
) -> Result<String, (StatusCode, Json<serde_json::Value>)> {
    let strategy_base = state.strategy_base_url.as_ref().ok_or((
        StatusCode::SERVICE_UNAVAILABLE,
        error_body(
            "config_error",
            "STRATEGY_BASE_URL not configured",
            "gateway",
        ),
    ))?;
    Ok(format!("{}{}", strategy_base.trim_end_matches('/'), path))
}
