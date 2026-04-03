use axum::{
    Json,
    extract::{Request, State},
    http::StatusCode,
    middleware::Next,
    response::{IntoResponse, Response},
};
use serde_json::json;

use crate::config::AppState;

pub async fn require_internal_token(
    State(state): State<AppState>,
    request: Request,
    next: Next,
) -> Response {
    let provided = request
        .headers()
        .get("X-Internal-Job-Token")
        .and_then(|value| value.to_str().ok())
        .map(str::trim)
        .unwrap_or("");

    if provided == state.config.internal_job_token {
        return next.run(request).await;
    }

    (
        StatusCode::FORBIDDEN,
        Json(json!({
            "success": false,
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Internal job token missing or invalid",
            }
        })),
    )
        .into_response()
}
