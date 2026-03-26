mod cache;
mod errors;
mod firebase;
mod jwt;
mod token;

use axum::{
    extract::{Request, State},
    http::StatusCode,
    middleware::Next,
    response::Response,
};
use tracing::debug;

use crate::gateway_types::{AppState, RequestContext};

use self::cache::{auth_cache_lookup, auth_cache_store};
use self::errors::auth_err;
use self::firebase::verify_firebase_token;
use self::jwt::validate_gateway_jwt;
use self::token::extract_bearer_token;

pub(crate) async fn require_gateway_jwt(
    State(state): State<AppState>,
    request: Request,
    next: Next,
) -> Result<Response, errors::AuthRejection> {
    if !state.jwt_auth.effective_required() {
        return Ok(next.run(request).await);
    }

    let request_id = request
        .extensions()
        .get::<RequestContext>()
        .map(|ctx| ctx.request_id.as_str())
        .unwrap_or("unknown")
        .to_string();

    let token = extract_bearer_token(&request).ok_or_else(|| {
        auth_err(
            StatusCode::UNAUTHORIZED,
            "auth_required",
            "missing bearer token",
            &request_id,
        )
    })?;

    validate_gateway_jwt(token, &state.jwt_auth).map_err(|reason| {
        auth_err(
            StatusCode::UNAUTHORIZED,
            "auth_verify_failed",
            reason,
            &request_id,
        )
    })?;

    Ok(next.run(request).await)
}

pub(crate) async fn require_firebase_auth(
    State(state): State<AppState>,
    request: Request,
    next: Next,
) -> Result<Response, errors::AuthRejection> {
    if !state.firebase_auth.required {
        return Ok(next.run(request).await);
    }

    let request_id = request
        .extensions()
        .get::<RequestContext>()
        .map(|ctx| ctx.request_id.as_str())
        .unwrap_or("unknown")
        .to_string();

    let token = extract_bearer_token(&request).ok_or_else(|| {
        auth_err(
            StatusCode::UNAUTHORIZED,
            "auth_required",
            "missing bearer token",
            &request_id,
        )
    })?;

    let api_key = state
        .firebase_auth
        .web_api_key
        .as_deref()
        .filter(|value| !value.trim().is_empty())
        .ok_or_else(|| {
            auth_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "config_error",
                "FIREBASE_WEB_API_KEY not configured",
                &request_id,
            )
        })?;

    let user = if let Some(cached) = auth_cache_lookup(&state, token).await {
        cached
    } else {
        let verified = verify_firebase_token(&state, api_key, token, &request_id).await?;
        auth_cache_store(&state, token, verified.clone()).await;
        verified
    };

    debug!(
        request_id = %request_id,
        uid = %user.uid,
        email = ?user.email,
        "firebase auth passed"
    );

    let mut request = request;
    request.extensions_mut().insert(user);
    Ok(next.run(request).await)
}
