use serde::Serialize;
use serde_json::{Map, Value, json};

use crate::policy::{
    ApprovalDecision, ApprovalDecisionKind, CancelDecision, CancelDecisionKind, DispatchDecision,
    DispatchDecisionKind, DispatchLane, RetryDecision, RetryDecisionKind,
};

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct ControlPlaneActionResponse {
    pub operation_id: String,
    pub current_state: String,
    pub decision: String,
    pub queued: bool,
    pub reason: String,
    pub correlation_id: String,
    pub managed_by: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub worker_key: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub lane: Option<DispatchLane>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub lease_expires_at_ms: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<Value>,
}

impl ControlPlaneActionResponse {
    #[must_use]
    pub fn from_dispatch_decision(decision: &DispatchDecision, correlation_id: &str) -> Self {
        Self {
            operation_id: decision.operation_id.clone(),
            current_state: decision.current_state.clone(),
            decision: dispatch_decision_name(decision.decision).to_string(),
            queued: decision.queued,
            reason: decision.reason.clone(),
            correlation_id: correlation_id.to_string(),
            managed_by: decision.managed_by.clone(),
            worker_key: decision.worker_key.clone(),
            lane: decision.lane,
            lease_expires_at_ms: decision.lease_expires_at_ms,
            error: None,
        }
    }

    #[must_use]
    pub fn from_approval_decision(
        decision: &ApprovalDecision,
        correlation_id: &str,
        queued: bool,
    ) -> Self {
        Self {
            operation_id: decision.operation_id.clone(),
            current_state: decision.current_state.clone(),
            decision: approval_decision_name(decision.decision).to_string(),
            queued,
            reason: decision.reason.clone(),
            correlation_id: correlation_id.to_string(),
            managed_by: decision.managed_by.clone(),
            worker_key: None,
            lane: None,
            lease_expires_at_ms: None,
            error: None,
        }
    }

    #[must_use]
    pub fn from_retry_decision(
        decision: &RetryDecision,
        correlation_id: &str,
        queued: bool,
    ) -> Self {
        Self {
            operation_id: decision.operation_id.clone(),
            current_state: decision.current_state.clone(),
            decision: retry_decision_name(decision.decision).to_string(),
            queued,
            reason: decision.reason.clone(),
            correlation_id: correlation_id.to_string(),
            managed_by: decision.managed_by.clone(),
            worker_key: None,
            lane: None,
            lease_expires_at_ms: None,
            error: None,
        }
    }

    #[must_use]
    pub fn from_cancel_decision(
        decision: &CancelDecision,
        correlation_id: &str,
        queued: bool,
    ) -> Self {
        Self {
            operation_id: decision.operation_id.clone(),
            current_state: decision.current_state.clone(),
            decision: cancel_decision_name(decision.decision).to_string(),
            queued,
            reason: decision.reason.clone(),
            correlation_id: correlation_id.to_string(),
            managed_by: decision.managed_by.clone(),
            worker_key: None,
            lane: None,
            lease_expires_at_ms: None,
            error: None,
        }
    }

    #[must_use]
    pub fn upstream_error(
        operation_id: impl Into<String>,
        correlation_id: &str,
        reason: impl Into<String>,
        error: Value,
    ) -> Self {
        Self {
            operation_id: operation_id.into(),
            current_state: "unknown".to_string(),
            decision: "upstream_error".to_string(),
            queued: false,
            reason: reason.into(),
            correlation_id: correlation_id.to_string(),
            managed_by: "sentinel_orchestrator".to_string(),
            worker_key: None,
            lane: None,
            lease_expires_at_ms: None,
            error: Some(error),
        }
    }
}

#[derive(Debug, Clone, Copy, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum NormalizedSseFrameKind {
    Snapshot,
    Event,
    Heartbeat,
    Closed,
    Error,
}

impl NormalizedSseFrameKind {
    #[must_use]
    pub fn event_name(self) -> &'static str {
        match self {
            Self::Snapshot => "snapshot",
            Self::Event => "event",
            Self::Heartbeat => "heartbeat",
            Self::Closed => "closed",
            Self::Error => "error",
        }
    }
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct NormalizedSseFrame {
    pub frame_type: NormalizedSseFrameKind,
    pub correlation_id: String,
    pub operation_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub event_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub event_type: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub payload: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<Value>,
}

impl NormalizedSseFrame {
    #[must_use]
    pub fn heartbeat(operation_id: &str, correlation_id: &str) -> Self {
        Self {
            frame_type: NormalizedSseFrameKind::Heartbeat,
            correlation_id: correlation_id.to_string(),
            operation_id: operation_id.to_string(),
            event_id: None,
            event_type: None,
            payload: None,
            error: None,
        }
    }
}

#[must_use]
pub fn normalize_upstream_sse_frame(
    raw_event: Option<&str>,
    raw_event_id: Option<&str>,
    data_lines: &[String],
    saw_comment: bool,
    correlation_id: &str,
    operation_id: &str,
) -> Option<(NormalizedSseFrameKind, String)> {
    if saw_comment && data_lines.is_empty() && raw_event.is_none() {
        let frame = NormalizedSseFrame::heartbeat(operation_id, correlation_id);
        return Some((frame.frame_type, encode_sse_frame(&frame)));
    }

    if raw_event.is_none() && data_lines.is_empty() {
        return None;
    }

    let upstream_event = raw_event.unwrap_or("operation.event");
    let raw_payload = data_lines.join("\n").trim().to_string();
    let event_id = raw_event_id.map(ToOwned::to_owned);

    let parsed_payload = if raw_payload.is_empty() {
        Ok(Value::Object(Map::new()))
    } else {
        serde_json::from_str::<Value>(&raw_payload)
            .map(normalize_payload_value)
            .map_err(|error| error.to_string())
    };

    let frame = match (upstream_event, parsed_payload) {
        (_, Err(error)) => NormalizedSseFrame {
            frame_type: NormalizedSseFrameKind::Error,
            correlation_id: correlation_id.to_string(),
            operation_id: operation_id.to_string(),
            event_id,
            event_type: raw_event.map(ToOwned::to_owned),
            payload: None,
            error: Some(json!({
                "code": "INVALID_UPSTREAM_SSE_PAYLOAD",
                "message": error,
            })),
        },
        ("operation.snapshot", Ok(payload)) => NormalizedSseFrame {
            frame_type: NormalizedSseFrameKind::Snapshot,
            correlation_id: correlation_id.to_string(),
            operation_id: operation_id.to_string(),
            event_id,
            event_type: Some("operation.snapshot".to_string()),
            payload: Some(payload),
            error: None,
        },
        ("operation.closed", Ok(payload)) => NormalizedSseFrame {
            frame_type: NormalizedSseFrameKind::Closed,
            correlation_id: correlation_id.to_string(),
            operation_id: operation_id.to_string(),
            event_id,
            event_type: Some("operation.closed".to_string()),
            payload: Some(payload),
            error: None,
        },
        ("operation.error", Ok(payload)) => NormalizedSseFrame {
            frame_type: NormalizedSseFrameKind::Error,
            correlation_id: correlation_id.to_string(),
            operation_id: operation_id.to_string(),
            event_id,
            event_type: Some("operation.error".to_string()),
            payload: Some(payload.clone()),
            error: Some(extract_error_payload(&payload)),
        },
        (event_type, Ok(payload)) => NormalizedSseFrame {
            frame_type: NormalizedSseFrameKind::Event,
            correlation_id: correlation_id.to_string(),
            operation_id: operation_id.to_string(),
            event_id,
            event_type: Some(event_type.to_string()),
            payload: Some(payload),
            error: None,
        },
    };

    Some((frame.frame_type, encode_sse_frame(&frame)))
}

#[must_use]
pub fn encode_sse_frame(frame: &NormalizedSseFrame) -> String {
    let mut lines = vec![format!("event: {}", frame.frame_type.event_name())];
    if let Some(event_id) = &frame.event_id {
        lines.push(format!("id: {event_id}"));
    }
    let payload = serde_json::to_string(frame).unwrap_or_else(|_| "{}".to_string());
    for line in payload.split('\n') {
        lines.push(format!("data: {line}"));
    }
    lines.push(String::new());
    lines.join("\n") + "\n"
}

fn normalize_payload_value(value: Value) -> Value {
    match value {
        Value::Object(_) => value,
        other => json!({ "value": other }),
    }
}

fn extract_error_payload(payload: &Value) -> Value {
    payload
        .as_object()
        .and_then(|object| object.get("error"))
        .cloned()
        .unwrap_or_else(|| {
            json!({
                "code": "UPSTREAM_STREAM_ERROR",
                "message": "Upstream stream emitted an error frame",
            })
        })
}

fn dispatch_decision_name(kind: DispatchDecisionKind) -> &'static str {
    match kind {
        DispatchDecisionKind::Accepted => "accepted",
        DispatchDecisionKind::AlreadyManaged => "already_managed",
        DispatchDecisionKind::SkippedNotQueued => "skipped_not_queued",
        DispatchDecisionKind::WorkerUnavailable => "worker_unavailable",
    }
}

fn approval_decision_name(kind: ApprovalDecisionKind) -> &'static str {
    match kind {
        ApprovalDecisionKind::EnqueueDispatch => "enqueue_dispatch",
        ApprovalDecisionKind::NoDispatchRequired => "no_dispatch_required",
    }
}

fn retry_decision_name(kind: RetryDecisionKind) -> &'static str {
    match kind {
        RetryDecisionKind::EnqueueDispatch => "enqueue_dispatch",
        RetryDecisionKind::NoDispatchRequired => "no_dispatch_required",
    }
}

fn cancel_decision_name(kind: CancelDecisionKind) -> &'static str {
    match kind {
        CancelDecisionKind::Cancelled => "cancelled",
        CancelDecisionKind::CancellationRequested => "cancellation_requested",
        CancelDecisionKind::AlreadyTerminal => "already_terminal",
    }
}

#[cfg(test)]
mod tests {
    use serde_json::json;

    use crate::policy::{DispatchLane, DispatchLease, duplicate_dispatch_decision};

    use super::{ControlPlaneActionResponse, NormalizedSseFrameKind, normalize_upstream_sse_frame};

    #[test]
    fn dispatch_response_includes_required_contract_fields() {
        let lease = DispatchLease::new(1, "op-1", Some(DispatchLane::Heavy), 100, 1000, "cp-1");
        let decision = duplicate_dispatch_decision("op-1", &lease);
        let response = ControlPlaneActionResponse::from_dispatch_decision(&decision, "cp-1");

        assert_eq!(response.operation_id, "op-1");
        assert_eq!(response.decision, "already_managed");
        assert_eq!(response.correlation_id, "cp-1");
        assert_eq!(response.lane, Some(DispatchLane::Heavy));
        assert_eq!(response.lease_expires_at_ms, Some(1100));
    }

    #[test]
    fn comment_keepalive_is_normalized_to_heartbeat_frame() {
        let normalized = normalize_upstream_sse_frame(None, None, &[], true, "cp-1", "op-1")
            .expect("heartbeat frame");

        assert_eq!(normalized.0, NormalizedSseFrameKind::Heartbeat);
        assert!(normalized.1.contains("event: heartbeat"));
        assert!(normalized.1.contains("\"correlation_id\":\"cp-1\""));
    }

    #[test]
    fn operation_state_is_wrapped_as_generic_event_frame() {
        let normalized = normalize_upstream_sse_frame(
            Some("operation.state"),
            Some("state-1"),
            &[json!({"status": "running", "progress": 25}).to_string()],
            false,
            "cp-2",
            "op-2",
        )
        .expect("event frame");

        assert_eq!(normalized.0, NormalizedSseFrameKind::Event);
        assert!(normalized.1.contains("event: event"));
        assert!(normalized.1.contains("\"event_type\":\"operation.state\""));
        assert!(normalized.1.contains("\"status\":\"running\""));
    }

    #[test]
    fn invalid_payload_is_normalized_to_error_frame() {
        let normalized = normalize_upstream_sse_frame(
            Some("operation.state"),
            None,
            &[String::from("{invalid-json}")],
            false,
            "cp-3",
            "op-3",
        )
        .expect("error frame");

        assert_eq!(normalized.0, NormalizedSseFrameKind::Error);
        assert!(normalized.1.contains("event: error"));
        assert!(normalized.1.contains("INVALID_UPSTREAM_SSE_PAYLOAD"));
    }
}
