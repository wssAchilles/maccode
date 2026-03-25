use axum::{
    extract::{Request, State},
    http::StatusCode,
    middleware::Next,
    response::Response,
    Json,
};
use serde::Deserialize;
use tracing::debug;

use crate::{
    gateway_types::{AppState, AuthenticatedUser, RequestContext},
    handlers::common::error_body,
};

#[derive(Deserialize)]
struct AccountsLookupResponse {
    users: Option<Vec<AccountsLookupUser>>,
}

#[derive(Deserialize)]
struct AccountsLookupUser {
    #[serde(rename = "localId")]
    local_id: String,
    email: Option<String>,
}

pub(crate) async fn require_firebase_auth(
    State(state): State<AppState>,
    request: Request,
    next: Next,
) -> Result<Response, (StatusCode, Json<serde_json::Value>)> {
    if !state.firebase_auth.required {
        return Ok(next.run(request).await);
    }

    let request_id = request
        .extensions()
        .get::<RequestContext>()
        .map(|ctx| ctx.request_id.as_str())
        .unwrap_or("unknown")
        .to_string();

    let token = extract_bearer_token(&request)
        .ok_or_else(|| auth_err(StatusCode::UNAUTHORIZED, "auth_required", "missing bearer token", &request_id))?;

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

    let user = verify_firebase_token(&state, api_key, token, &request_id).await?;
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

fn extract_bearer_token(request: &Request) -> Option<&str> {
    request
        .headers()
        .get("authorization")
        .and_then(|value| value.to_str().ok())
        .map(str::trim)
        .and_then(|raw| raw.strip_prefix("Bearer ").or_else(|| raw.strip_prefix("bearer ")))
        .map(str::trim)
        .filter(|token| !token.is_empty())
}

async fn verify_firebase_token(
    state: &AppState,
    api_key: &str,
    token: &str,
    request_id: &str,
) -> Result<AuthenticatedUser, (StatusCode, Json<serde_json::Value>)> {
    let response = state
        .http_client
        .post(format!(
            "https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={api_key}"
        ))
        .json(&serde_json::json!({ "idToken": token }))
        .send()
        .await
        .map_err(|err| {
            auth_err(
                StatusCode::UNAUTHORIZED,
                "auth_verify_failed",
                format!("token verify request failed: {err}"),
                request_id,
            )
        })?;

    if !response.status().is_success() {
        let status = response.status().as_u16();
        let body = response
            .text()
            .await
            .unwrap_or_else(|_| "failed to decode auth error body".to_string());
        return Err(auth_err(
            StatusCode::UNAUTHORIZED,
            "auth_verify_failed",
            format!("token rejected [{status}]: {body}"),
            request_id,
        ));
    }

    let payload = response
        .json::<AccountsLookupResponse>()
        .await
        .map_err(|err| {
            auth_err(
                StatusCode::UNAUTHORIZED,
                "auth_verify_failed",
                format!("token verify decode failed: {err}"),
                request_id,
            )
        })?;

    let user = payload
        .users
        .and_then(|users| users.into_iter().next())
        .filter(|candidate| !candidate.local_id.trim().is_empty())
        .ok_or_else(|| {
            auth_err(
                StatusCode::UNAUTHORIZED,
                "auth_verify_failed",
                "token lookup returned empty user",
                request_id,
            )
        })?;

    Ok(AuthenticatedUser {
        uid: user.local_id,
        email: user.email,
    })
}

fn auth_err(
    status: StatusCode,
    code: &str,
    message: impl Into<String>,
    request_id: &str,
) -> (StatusCode, Json<serde_json::Value>) {
    (status, error_body(code, message.into(), request_id))
}
