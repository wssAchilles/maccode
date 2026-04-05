"""Approval-policy helpers for operation control flow."""

from __future__ import annotations

from typing import Any, Dict, Optional

from services.compute_rollout_operation_service import (
    infer_rollout_change_approval_policy,
)


def default_approval_policy(
    required: bool = False,
    *,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    policy = {
        'required': required,
        'mode': 'manual' if required else 'auto',
        'reason': reason,
    }
    return {key: value for key, value in policy.items() if value is not None}


def infer_approval_policy(
    operation_type: str,
    payload: Dict[str, Any],
    explicit_policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if explicit_policy:
        return {
            'required': bool(explicit_policy.get('required')),
            'mode': explicit_policy.get(
                'mode',
                'manual' if explicit_policy.get('required') else 'auto',
            ),
            'reason': explicit_policy.get('reason'),
        }

    if operation_type == 'rag_ingest' and bool(payload.get('reset')):
        return default_approval_policy(
            True,
            reason='Resetting an existing knowledge collection requires approval',
        )
    if operation_type in {'ml_train', 'train_model'} and bool(
        payload.get('overwrite_existing')
        or payload.get('replace_existing_model')
        or payload.get('force_overwrite_artifact')
    ):
        return default_approval_policy(
            True,
            reason='Overwriting an existing model artifact requires approval',
        )
    if operation_type == 'optimization' and int(payload.get('scenario_count', 0) or 0) >= 100:
        return default_approval_policy(
            True,
            reason='Large-scale optimization requires approval',
        )
    if operation_type == 'compute_rollout_change':
        inferred = infer_rollout_change_approval_policy(payload)
        return default_approval_policy(
            bool(inferred.get('required')),
            reason=inferred.get('reason'),
        )
    return default_approval_policy(False)


def approval_state_from_policy(policy: Dict[str, Any]) -> Dict[str, Any]:
    required = bool(policy.get('required'))
    return {
        'required': required,
        'state': 'pending' if required else 'not_required',
        'reason': policy.get('reason'),
        'approved_by': None,
        'approved_at': None,
        'message': None,
    }
