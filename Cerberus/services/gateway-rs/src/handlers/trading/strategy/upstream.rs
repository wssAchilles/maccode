mod circuit;
mod error;
mod metrics;
mod queue;

use std::time::Duration;

use reqwest::{RequestBuilder, Response, StatusCode};

use crate::gateway_types::AppState;
use crate::gateway_utils::with_strategy_internal_auth;
use circuit::{check_circuit_open, record_circuit_rejection, record_failure, record_success};
pub(crate) use error::StrategyUpstreamError;
use metrics::{increment_upstream_requests, record_auth_failure};
use queue::acquire_upstream_slot;

pub(crate) async fn send_strategy_request(
    state: &AppState,
    request: RequestBuilder,
    timeout_ms: u64,
) -> Result<Response, StrategyUpstreamError> {
    if let Some(retry_after_ms) = check_circuit_open(state).await {
        record_circuit_rejection(state, retry_after_ms).await;
        return Err(StrategyUpstreamError::CircuitOpen { retry_after_ms });
    }

    let permit = acquire_upstream_slot(state).await?;
    increment_upstream_requests(state).await;

    let request = match with_strategy_internal_auth(state, request).await {
        Ok(request) => request,
        Err(err) => {
            let reason = err.to_string();
            record_auth_failure(state, reason.clone()).await;
            record_failure(state, reason.clone(), true).await;
            return Err(StrategyUpstreamError::AuthFailed(reason));
        }
    };

    let response_result = request
        .timeout(Duration::from_millis(timeout_ms))
        .send()
        .await
        .map_err(|err| StrategyUpstreamError::RequestFailed(err.to_string()));

    drop(permit);

    match &response_result {
        Ok(response) => {
            let status = response.status();
            if is_failure_status(status) {
                record_failure(state, format!("status={}", status.as_u16()), true).await;
            } else {
                record_success(state).await;
            }
        }
        Err(StrategyUpstreamError::RequestFailed(reason)) => {
            record_failure(state, reason.clone(), true).await;
        }
        Err(StrategyUpstreamError::AuthFailed(_)) => {}
        Err(StrategyUpstreamError::CircuitOpen { .. })
        | Err(StrategyUpstreamError::QueueSaturated { .. }) => {}
    }

    response_result
}

fn is_failure_status(status: StatusCode) -> bool {
    status.is_server_error()
        || matches!(
            status,
            StatusCode::UNAUTHORIZED
                | StatusCode::FORBIDDEN
                | StatusCode::TOO_MANY_REQUESTS
                | StatusCode::REQUEST_TIMEOUT
        )
}
