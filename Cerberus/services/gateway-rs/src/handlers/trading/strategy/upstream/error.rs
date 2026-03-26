pub(crate) enum StrategyUpstreamError {
    CircuitOpen { retry_after_ms: u64 },
    QueueSaturated { waited_ms: u64 },
    AuthFailed(String),
    RequestFailed(String),
}

impl StrategyUpstreamError {
    pub(crate) fn retry_after_ms(&self) -> Option<u64> {
        match self {
            StrategyUpstreamError::CircuitOpen { retry_after_ms } => Some(*retry_after_ms),
            StrategyUpstreamError::QueueSaturated { .. }
            | StrategyUpstreamError::AuthFailed(_)
            | StrategyUpstreamError::RequestFailed(_) => None,
        }
    }

    pub(crate) fn telemetry_reason(&self) -> String {
        match self {
            StrategyUpstreamError::CircuitOpen { retry_after_ms } => {
                format!("circuit_open retry_after_ms={retry_after_ms}")
            }
            StrategyUpstreamError::QueueSaturated { waited_ms } => {
                format!("queue_saturated waited_ms={waited_ms}")
            }
            StrategyUpstreamError::AuthFailed(reason) => format!("auth_failed: {reason}"),
            StrategyUpstreamError::RequestFailed(reason) => format!("request_failed: {reason}"),
        }
    }

    pub(crate) fn client_message(&self) -> String {
        match self {
            StrategyUpstreamError::CircuitOpen { retry_after_ms } => {
                format!("strategy upstream circuit open, retry after {retry_after_ms}ms")
            }
            StrategyUpstreamError::QueueSaturated { waited_ms } => {
                format!("strategy upstream queue saturated (waited {waited_ms}ms)")
            }
            StrategyUpstreamError::AuthFailed(reason)
            | StrategyUpstreamError::RequestFailed(reason) => reason.clone(),
        }
    }
}
