use axum::{
    extract::{Request, State},
    http::StatusCode,
    middleware::Next,
    response::Response,
    Json,
};
use jsonwebtoken::{decode, Algorithm, DecodingKey, Validation};
use serde::Deserialize;
use tracing::debug;

use crate::{
    gateway_types::{AppState, AuthenticatedUser, CachedAuthUser, JwtAuthConfig, RequestContext},
    gateway_utils::current_millis,
    handlers::common::{error_body, error_body_code, GatewayErrorCode},
};

const AUTH_CACHE_TTL_MS: u64 = 60_000;
const AUTH_CACHE_MAX_ENTRIES: usize = 1024;

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

#[derive(Deserialize)]
struct GatewayJwtClaims {
    sub: Option<String>,
    iss: Option<String>,
    aud: Option<serde_json::Value>,
    exp: usize,
}

pub(crate) async fn require_gateway_jwt(
    State(state): State<AppState>,
    request: Request,
    next: Next,
) -> Result<Response, (StatusCode, Json<serde_json::Value>)> {
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
            GatewayErrorCode::AuthRequired.as_str(),
            "missing bearer token",
            &request_id,
        )
    })?;

    validate_gateway_jwt(token, &state.jwt_auth).map_err(|reason| {
        auth_err(
            StatusCode::UNAUTHORIZED,
            GatewayErrorCode::AuthVerifyFailed.as_str(),
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

    let token = extract_bearer_token(&request).ok_or_else(|| {
        auth_err(
            StatusCode::UNAUTHORIZED,
            GatewayErrorCode::AuthRequired.as_str(),
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
                GatewayErrorCode::ConfigError.as_str(),
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

async fn auth_cache_lookup(state: &AppState, token: &str) -> Option<AuthenticatedUser> {
    let now = current_millis();
    let cache = state.auth_cache.read().await;
    cache.get(token).and_then(|entry| {
        if entry.expires_at_ms > now {
            Some(entry.user.clone())
        } else {
            None
        }
    })
}

async fn auth_cache_store(state: &AppState, token: &str, user: AuthenticatedUser) {
    let now = current_millis();
    let mut cache = state.auth_cache.write().await;
    cache.retain(|_, entry| entry.expires_at_ms > now);
    if cache.len() >= AUTH_CACHE_MAX_ENTRIES {
        cache.clear();
    }
    cache.insert(
        token.to_string(),
        CachedAuthUser {
            user,
            expires_at_ms: now + AUTH_CACHE_TTL_MS,
        },
    );
}

fn extract_bearer_token(request: &Request) -> Option<&str> {
    request
        .headers()
        .get("authorization")
        .and_then(|value| value.to_str().ok())
        .map(str::trim)
        .and_then(|raw| {
            raw.strip_prefix("Bearer ")
                .or_else(|| raw.strip_prefix("bearer "))
        })
        .map(str::trim)
        .filter(|token| !token.is_empty())
}

fn validate_gateway_jwt(token: &str, cfg: &JwtAuthConfig) -> Result<(), String> {
    let secret = cfg
        .hs256_secret
        .as_deref()
        .filter(|value| !value.trim().is_empty())
        .ok_or_else(|| "JWT_HS256_SECRET not configured".to_string())?;
    let mut validation = Validation::new(Algorithm::HS256);
    validation.validate_exp = true;
    let token_data = decode::<GatewayJwtClaims>(
        token,
        &DecodingKey::from_secret(secret.as_bytes()),
        &validation,
    )
    .map_err(|err| format!("jwt decode failed: {err}"))?;
    validate_claims(token_data.claims, cfg)
}

fn validate_claims(claims: GatewayJwtClaims, cfg: &JwtAuthConfig) -> Result<(), String> {
    if claims.sub.as_deref().is_none() {
        return Err("jwt subject missing".to_string());
    }
    if claims.exp == 0 {
        return Err("jwt expiration missing".to_string());
    }
    if let Some(expected_iss) = cfg.issuer.as_deref() {
        if claims.iss.as_deref() != Some(expected_iss) {
            return Err("jwt issuer mismatch".to_string());
        }
    }
    if let Some(expected_aud) = cfg.audience.as_deref() {
        if !audience_matches(claims.aud.as_ref(), expected_aud) {
            return Err("jwt audience mismatch".to_string());
        }
    }
    Ok(())
}

fn audience_matches(raw: Option<&serde_json::Value>, expected: &str) -> bool {
    let Some(aud) = raw else {
        return false;
    };
    if let Some(single) = aud.as_str() {
        return single == expected;
    }
    if let Some(list) = aud.as_array() {
        return list
            .iter()
            .filter_map(|value| value.as_str())
            .any(|item| item == expected);
    }
    false
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
                GatewayErrorCode::AuthVerifyFailed.as_str(),
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
            GatewayErrorCode::AuthVerifyFailed.as_str(),
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
                GatewayErrorCode::AuthVerifyFailed.as_str(),
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
                GatewayErrorCode::AuthVerifyFailed.as_str(),
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
    if let Some(known) = to_known_code(code) {
        (status, error_body_code(known, message.into(), request_id))
    } else {
        (status, error_body(code, message.into(), request_id))
    }
}

fn to_known_code(code: &str) -> Option<GatewayErrorCode> {
    match code {
        "validation_error" => Some(GatewayErrorCode::ValidationError),
        "config_error" => Some(GatewayErrorCode::ConfigError),
        "upstream_error" => Some(GatewayErrorCode::UpstreamError),
        "upstream_request_failed" => Some(GatewayErrorCode::UpstreamRequestFailed),
        "upstream_decode_failed" => Some(GatewayErrorCode::UpstreamDecodeFailed),
        "upstream_status_error" => Some(GatewayErrorCode::UpstreamStatusError),
        "internal_error" => Some(GatewayErrorCode::InternalError),
        "auth_required" => Some(GatewayErrorCode::AuthRequired),
        "auth_verify_failed" => Some(GatewayErrorCode::AuthVerifyFailed),
        "signature_error" => Some(GatewayErrorCode::SignatureError),
        _ => None,
    }
}
