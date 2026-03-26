use std::time::Duration;

use anyhow::{bail, Context};

use crate::gateway_types::AppState;

const METADATA_FLAVOR_HEADER: &str = "Metadata-Flavor";
const METADATA_FLAVOR_VALUE: &str = "Google";

pub(super) async fn fetch_strategy_identity_token(
    state: &AppState,
    audience: &str,
) -> anyhow::Result<String> {
    let response = state
        .http_client
        .get(state.strategy_internal_auth.metadata_identity_url.as_str())
        .query(&[("audience", audience), ("format", "full")])
        .header(METADATA_FLAVOR_HEADER, METADATA_FLAVOR_VALUE)
        .timeout(Duration::from_millis(1_500))
        .send()
        .await
        .context("metadata identity request failed")?;

    let status = response.status();
    let raw_body = response
        .text()
        .await
        .context("metadata identity response read failed")?;
    if !status.is_success() {
        let trimmed = raw_body.trim();
        let body = if trimmed.is_empty() {
            "<empty>"
        } else {
            trimmed
        };
        bail!(
            "metadata identity request status={} body={}",
            status.as_u16(),
            body
        );
    }
    let token = raw_body.trim();
    if token.is_empty() {
        bail!("metadata identity returned empty token");
    }
    Ok(token.to_string())
}
