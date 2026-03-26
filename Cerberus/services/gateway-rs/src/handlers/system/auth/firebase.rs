use axum::http::StatusCode;
use serde::Deserialize;

use crate::gateway_types::{AppState, AuthenticatedUser};

use super::errors::{auth_err, AuthRejection};

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

pub(super) async fn verify_firebase_token(
    state: &AppState,
    api_key: &str,
    token: &str,
    request_id: &str,
) -> Result<AuthenticatedUser, AuthRejection> {
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
