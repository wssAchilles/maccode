use axum::extract::Request;

pub(super) fn extract_bearer_token(request: &Request) -> Option<&str> {
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
