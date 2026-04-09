use serde::{Deserialize, Serialize};

pub const CONTROL_PLANE_MANAGER: &str = "sentinel_orchestrator";
pub const CONTROL_PLANE_POLICY_VERSION: &str = "delta5-connector-lifecycle-v1";

const HEAVY_OPERATION_TYPES: &[&str] = &["ml_train", "rag_ingest"];
const TERMINAL_STATUSES: &[&str] = &["completed", "failed", "cancelled"];

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct ApprovalStateSnapshot {
    #[serde(default)]
    pub state: String,
    #[serde(default)]
    pub required: bool,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct OperationSnapshot {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub job_id: String,
    #[serde(default)]
    pub r#type: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub execution_target: String,
    #[serde(default)]
    pub control_task_id: Option<String>,
    #[serde(default)]
    pub approval_state: ApprovalStateSnapshot,
}

impl OperationSnapshot {
    #[must_use]
    #[cfg(test)]
    pub fn queued(operation_id: impl Into<String>, operation_type: impl Into<String>) -> Self {
        let operation_id = operation_id.into();
        Self {
            id: operation_id.clone(),
            job_id: operation_id,
            r#type: operation_type.into(),
            status: "queued".to_string(),
            execution_target: "python_worker".to_string(),
            control_task_id: None,
            approval_state: ApprovalStateSnapshot::default(),
        }
    }

    #[must_use]
    pub fn operation_id(&self) -> String {
        if !self.id.is_empty() {
            return self.id.clone();
        }
        self.job_id.clone()
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum DispatchLane {
    Light,
    Heavy,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DispatchLease {
    pub lease_id: u64,
    pub operation_id: String,
    pub correlation_id: String,
    pub lane: Option<DispatchLane>,
    pub acquired_at_ms: u64,
    pub expires_at_ms: u64,
}

impl DispatchLease {
    #[must_use]
    pub fn new(
        lease_id: u64,
        operation_id: impl Into<String>,
        lane: Option<DispatchLane>,
        acquired_at_ms: u64,
        ttl_ms: u64,
        correlation_id: impl Into<String>,
    ) -> Self {
        Self {
            lease_id,
            operation_id: operation_id.into(),
            correlation_id: correlation_id.into(),
            lane,
            acquired_at_ms,
            expires_at_ms: acquired_at_ms.saturating_add(ttl_ms),
        }
    }

    #[must_use]
    pub fn is_active_at(&self, now_ms: u64) -> bool {
        now_ms <= self.expires_at_ms
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum DispatchDecisionKind {
    Accepted,
    AlreadyManaged,
    SkippedNotQueued,
    WorkerUnavailable,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ApprovalDecisionKind {
    EnqueueDispatch,
    NoDispatchRequired,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum RetryDecisionKind {
    EnqueueDispatch,
    NoDispatchRequired,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum CancelDecisionKind {
    Cancelled,
    CancellationRequested,
    AlreadyTerminal,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DispatchDecision {
    pub operation_id: String,
    pub current_state: String,
    pub decision: DispatchDecisionKind,
    pub queued: bool,
    pub reason: String,
    pub managed_by: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub worker_key: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub lane: Option<DispatchLane>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub lease_expires_at_ms: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ApprovalDecision {
    pub operation_id: String,
    pub current_state: String,
    pub decision: ApprovalDecisionKind,
    pub should_enqueue_dispatch: bool,
    pub reason: String,
    pub managed_by: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RetryDecision {
    pub operation_id: String,
    pub current_state: String,
    pub decision: RetryDecisionKind,
    pub should_enqueue_dispatch: bool,
    pub reason: String,
    pub managed_by: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CancelDecision {
    pub operation_id: String,
    pub current_state: String,
    pub decision: CancelDecisionKind,
    pub reason: String,
    pub managed_by: String,
}

#[must_use]
pub fn classify_dispatch_lane(operation: &OperationSnapshot) -> DispatchLane {
    if operation.execution_target == "heavy_worker"
        || HEAVY_OPERATION_TYPES.contains(&operation.r#type.as_str())
    {
        return DispatchLane::Heavy;
    }
    DispatchLane::Light
}

#[must_use]
pub fn evaluate_dispatch_decision(
    operation: &OperationSnapshot,
    worker_key: Option<&str>,
) -> DispatchDecision {
    let operation_id = operation.operation_id();
    if operation.status != "queued" {
        return DispatchDecision {
            operation_id,
            current_state: operation.status.clone(),
            decision: DispatchDecisionKind::SkippedNotQueued,
            queued: false,
            reason: "Operation is not queued; dispatch skipped".to_string(),
            managed_by: CONTROL_PLANE_MANAGER.to_string(),
            worker_key: worker_key.map(ToOwned::to_owned),
            lane: Some(classify_dispatch_lane(operation)),
            lease_expires_at_ms: None,
        };
    }

    let lane = classify_dispatch_lane(operation);
    match worker_key {
        Some(worker_key) => DispatchDecision {
            operation_id,
            current_state: operation.status.clone(),
            decision: DispatchDecisionKind::Accepted,
            queued: true,
            reason: "Dispatch accepted by orchestrator policy".to_string(),
            managed_by: CONTROL_PLANE_MANAGER.to_string(),
            worker_key: Some(worker_key.to_string()),
            lane: Some(lane),
            lease_expires_at_ms: None,
        },
        None => DispatchDecision {
            operation_id,
            current_state: operation.status.clone(),
            decision: DispatchDecisionKind::WorkerUnavailable,
            queued: false,
            reason: "No worker target is currently available for dispatch".to_string(),
            managed_by: CONTROL_PLANE_MANAGER.to_string(),
            worker_key: None,
            lane: Some(lane),
            lease_expires_at_ms: None,
        },
    }
}

#[must_use]
pub fn duplicate_dispatch_decision(
    operation_id: impl Into<String>,
    lease: &DispatchLease,
) -> DispatchDecision {
    DispatchDecision {
        operation_id: operation_id.into(),
        current_state: "dispatching".to_string(),
        decision: DispatchDecisionKind::AlreadyManaged,
        queued: false,
        reason: "Operation is already managed by an active dispatch lease".to_string(),
        managed_by: CONTROL_PLANE_MANAGER.to_string(),
        worker_key: None,
        lane: lease.lane,
        lease_expires_at_ms: Some(lease.expires_at_ms),
    }
}

#[must_use]
pub fn accepted_dispatch_decision(
    operation_id: impl Into<String>,
    lease: &DispatchLease,
) -> DispatchDecision {
    DispatchDecision {
        operation_id: operation_id.into(),
        current_state: "queued".to_string(),
        decision: DispatchDecisionKind::Accepted,
        queued: true,
        reason: "Dispatch lease acquired in orchestrator".to_string(),
        managed_by: CONTROL_PLANE_MANAGER.to_string(),
        worker_key: None,
        lane: lease.lane,
        lease_expires_at_ms: Some(lease.expires_at_ms),
    }
}

#[must_use]
pub fn evaluate_approval_decision(
    operation: &OperationSnapshot,
    approved: bool,
) -> ApprovalDecision {
    let should_enqueue_dispatch = approved && operation.status == "queued";
    ApprovalDecision {
        operation_id: operation.operation_id(),
        current_state: operation.status.clone(),
        decision: if should_enqueue_dispatch {
            ApprovalDecisionKind::EnqueueDispatch
        } else {
            ApprovalDecisionKind::NoDispatchRequired
        },
        should_enqueue_dispatch,
        reason: if should_enqueue_dispatch {
            "Approval resolved to queued; dispatch should be enqueued".to_string()
        } else if approved {
            "Approval resolved without a queued state; no dispatch follow-up required".to_string()
        } else {
            "Operation was rejected; no dispatch follow-up required".to_string()
        },
        managed_by: CONTROL_PLANE_MANAGER.to_string(),
    }
}

#[must_use]
pub fn evaluate_retry_decision(operation: &OperationSnapshot) -> RetryDecision {
    let should_enqueue_dispatch = operation.status == "queued";
    RetryDecision {
        operation_id: operation.operation_id(),
        current_state: operation.status.clone(),
        decision: if should_enqueue_dispatch {
            RetryDecisionKind::EnqueueDispatch
        } else {
            RetryDecisionKind::NoDispatchRequired
        },
        should_enqueue_dispatch,
        reason: if should_enqueue_dispatch {
            "Retry returned the operation to queued; dispatch should be enqueued".to_string()
        } else {
            "Retry did not return the operation to queued; no dispatch follow-up required"
                .to_string()
        },
        managed_by: CONTROL_PLANE_MANAGER.to_string(),
    }
}

#[must_use]
pub fn evaluate_cancel_decision(operation: &OperationSnapshot) -> CancelDecision {
    let decision = if operation.status == "cancelled" {
        CancelDecisionKind::Cancelled
    } else if TERMINAL_STATUSES.contains(&operation.status.as_str()) {
        CancelDecisionKind::AlreadyTerminal
    } else {
        CancelDecisionKind::CancellationRequested
    };

    let reason = match decision {
        CancelDecisionKind::AlreadyTerminal => {
            "Operation is already terminal; cancel is a no-op".to_string()
        }
        CancelDecisionKind::Cancelled => "Operation transitioned to cancelled".to_string(),
        CancelDecisionKind::CancellationRequested => {
            "Cancellation was requested for an in-flight operation".to_string()
        }
    };

    CancelDecision {
        operation_id: operation.operation_id(),
        current_state: operation.status.clone(),
        decision,
        reason,
        managed_by: CONTROL_PLANE_MANAGER.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dispatch_lane_prefers_execution_target_and_heavy_operation_types() {
        let heavy_target = OperationSnapshot {
            execution_target: "heavy_worker".to_string(),
            ..OperationSnapshot::queued("op-heavy-target", "analysis")
        };
        assert_eq!(classify_dispatch_lane(&heavy_target), DispatchLane::Heavy);

        let ml_train = OperationSnapshot::queued("op-ml", "ml_train");
        assert_eq!(classify_dispatch_lane(&ml_train), DispatchLane::Heavy);

        let light = OperationSnapshot::queued("op-analysis", "analysis");
        assert_eq!(classify_dispatch_lane(&light), DispatchLane::Light);
    }

    #[test]
    fn dispatch_decision_skips_non_queued_operations() {
        let mut operation = OperationSnapshot::queued("op-running", "analysis");
        operation.status = "running".to_string();

        let decision = evaluate_dispatch_decision(&operation, Some("python_worker"));

        assert_eq!(decision.decision, DispatchDecisionKind::SkippedNotQueued);
        assert!(!decision.queued);
        assert_eq!(decision.current_state, "running");
    }

    #[test]
    fn approval_decision_only_requeues_when_operation_is_approved_and_queued() {
        let queued = OperationSnapshot::queued("op-approved", "analysis");
        let approved = evaluate_approval_decision(&queued, true);
        assert_eq!(approved.decision, ApprovalDecisionKind::EnqueueDispatch);
        assert!(approved.should_enqueue_dispatch);

        let mut waiting = OperationSnapshot::queued("op-rejected", "analysis");
        waiting.status = "cancelled".to_string();
        let rejected = evaluate_approval_decision(&waiting, false);
        assert_eq!(rejected.decision, ApprovalDecisionKind::NoDispatchRequired);
        assert!(!rejected.should_enqueue_dispatch);
    }

    #[test]
    fn retry_decision_requeues_when_operation_returns_to_queued() {
        let queued = OperationSnapshot::queued("op-retry", "analysis");
        let decision = evaluate_retry_decision(&queued);
        assert_eq!(decision.decision, RetryDecisionKind::EnqueueDispatch);
        assert!(decision.should_enqueue_dispatch);

        let mut running = OperationSnapshot::queued("op-running", "analysis");
        running.status = "running".to_string();
        let no_dispatch = evaluate_retry_decision(&running);
        assert_eq!(no_dispatch.decision, RetryDecisionKind::NoDispatchRequired);
        assert!(!no_dispatch.should_enqueue_dispatch);
    }

    #[test]
    fn dispatch_lease_expires_when_ttl_is_exhausted() {
        let lease = DispatchLease::new(
            7,
            "op-lease",
            Some(DispatchLane::Heavy),
            1_000,
            5_000,
            "cp-lease",
        );
        assert!(lease.is_active_at(5_999));
        assert!(!lease.is_active_at(6_001));
    }
}
