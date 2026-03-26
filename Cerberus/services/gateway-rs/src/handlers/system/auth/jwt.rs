use jsonwebtoken::{decode, Algorithm, DecodingKey, Validation};
use serde::Deserialize;

use crate::gateway_types::JwtAuthConfig;

#[derive(Deserialize)]
struct GatewayJwtClaims {
    sub: Option<String>,
    iss: Option<String>,
    aud: Option<serde_json::Value>,
    exp: usize,
}

pub(super) fn validate_gateway_jwt(token: &str, cfg: &JwtAuthConfig) -> Result<(), String> {
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
