use axum::http::StatusCode;
use hmac::{Hmac, Mac};
use sha2::Sha256;

pub(crate) fn sign_binance_query(
    secret: &str,
    query: &str,
) -> Result<String, (StatusCode, String)> {
    let mut mac = Hmac::<Sha256>::new_from_slice(secret.as_bytes()).map_err(|_| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            "invalid hmac key".to_string(),
        )
    })?;
    mac.update(query.as_bytes());
    let signature = mac.finalize().into_bytes();
    Ok(hex::encode(signature))
}
