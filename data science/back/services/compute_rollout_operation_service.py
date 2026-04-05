"""Domain logic for audited compute rollout change operations."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Tuple

from services.compute_benchmark_gate_service import ComputeBenchmarkGateService
from services.compute_governance_status_service import ComputeGovernanceStatusService
from services.compute_rollout_service import ComputeRolloutService
from utils.exceptions import ValidationError


def _clean_note(value: Any) -> str:
    return str(value or '').strip()[:240]


def _clean_patch(component: str, patch: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(patch, dict):
        raise ValidationError('target_policy 必须是对象')

    allowed_fields = {
        'rollout_mode',
        'preferred_backend',
        'canary_percent',
        'require_benchmark',
        'notes',
    }
    sanitized = {
        key: value
        for key, value in patch.items()
        if key in allowed_fields
    }
    if not sanitized:
        raise ValidationError('target_policy 不能为空')

    preview = ComputeRolloutService.preview_component_policy(component, sanitized)
    if not preview:
        raise ValidationError('无效的计算组件')
    return sanitized


def _coerce_rollout_patch(
    component: str,
    patch: Dict[str, Any],
    *,
    current_policy: Dict[str, Any],
) -> Dict[str, Any]:
    normalized = dict(patch)
    rollout_mode = str(
        normalized.get('rollout_mode')
        or current_policy.get('rollout_mode')
        or ''
    )
    current_canary = int(current_policy.get('canary_percent') or 0)

    if component == 'feature_engineering':
        if rollout_mode == 'python_stable':
            normalized.setdefault('preferred_backend', 'python_pandas')
            normalized.setdefault('canary_percent', 0)
        elif rollout_mode == 'native_candidate':
            normalized.setdefault('preferred_backend', 'native_cpp')
            normalized.setdefault(
                'canary_percent',
                current_canary if 0 < current_canary < 100 else 10,
            )
        elif rollout_mode == 'native_enforced':
            normalized.setdefault('preferred_backend', 'native_cpp')
            normalized.setdefault('canary_percent', 100)
    elif component == 'scenario_simulation':
        if rollout_mode == 'python_loop':
            normalized.setdefault('preferred_backend', 'python_loop')
            normalized.setdefault('canary_percent', 0)
        elif rollout_mode == 'vectorized_python':
            normalized.setdefault('preferred_backend', 'python_vectorized')
            normalized.setdefault('canary_percent', 100)

    return normalized


def _get_component_runtime_status(component: str) -> Dict[str, Any]:
    policy_view = ComputeGovernanceStatusService.get_policy_view()
    return next(
        (
            item
            for item in policy_view.get('components', [])
            if isinstance(item, dict) and str(item.get('key') or '') == component
        ),
        {},
    )


def _validate_runtime_readiness(
    component: str,
    preview_policy: Dict[str, Any],
    *,
    component_status: Dict[str, Any],
) -> None:
    rollout_mode = str(preview_policy.get('rollout_mode') or '')
    if component != 'feature_engineering':
        return
    if rollout_mode not in {'native_candidate', 'native_enforced'}:
        return

    benchmark_gate = ComputeBenchmarkGateService.summarize_policy(preview_policy)
    benchmark_ready = bool(benchmark_gate.get('benchmark_ready'))
    require_benchmark = bool(preview_policy.get('require_benchmark'))
    native_ready_targets = list(component_status.get('native_ready_targets') or [])
    rollout_blocker = str(component_status.get('rollout_blocker') or '').strip()

    if require_benchmark and not benchmark_ready:
        raise ValidationError(
            str(benchmark_gate.get('benchmark_summary') or 'Native rollout 需要先完成 benchmark 准入验证'),
        )
    if not native_ready_targets:
        raise ValidationError(rollout_blocker or '当前没有可用的 native-capable worker')


def _component_label(component: str) -> str:
    metadata = ComputeRolloutService.COMPONENT_METADATA.get(component) or {}
    return str(metadata.get('label') or component)


def _build_summary(before_policy: Dict[str, Any], after_policy: Dict[str, Any]) -> str:
    before_mode = str(before_policy.get('rollout_mode') or '--')
    after_mode = str(after_policy.get('rollout_mode') or '--')
    if before_mode == after_mode:
        return f'计算治理审计已确认，保持 {after_mode}'
    return f'计算治理已从 {before_mode} 切换到 {after_mode}'


def _build_rollback_patch(before_policy: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'rollout_mode': before_policy.get('rollout_mode'),
        'preferred_backend': before_policy.get('preferred_backend'),
        'canary_percent': before_policy.get('canary_percent'),
        'require_benchmark': before_policy.get('require_benchmark'),
        'notes': before_policy.get('notes') or '',
    }


def normalize_rollout_change_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    component = str(payload.get('component') or '').strip()
    if component not in ComputeRolloutService.COMPONENT_METADATA:
        raise ValidationError('不支持的计算治理组件')

    target_policy = payload.get('target_policy')
    if not isinstance(target_policy, dict):
        legacy_rollout_mode = payload.get('rollout_mode')
        if legacy_rollout_mode:
            target_policy = {'rollout_mode': legacy_rollout_mode}
        else:
            raise ValidationError('target_policy 缺失')

    before_policy = deepcopy(
        ComputeRolloutService.get_component_policy(component, force_refresh=True),
    )
    patch = _coerce_rollout_patch(
        component,
        _clean_patch(component, target_policy),
        current_policy=before_policy,
    )
    change_reason = _clean_note(payload.get('change_reason'))
    request_kind = str(payload.get('request_kind') or 'rollout_change').strip() or 'rollout_change'

    after_policy = ComputeRolloutService.preview_component_policy(component, patch, updated_by='preview')
    component_status = _get_component_runtime_status(component)
    _validate_runtime_readiness(
        component,
        after_policy,
        component_status=component_status,
    )
    summary = _build_summary(before_policy, after_policy)

    return {
        'component': component,
        'component_label': _component_label(component),
        'target_policy': patch,
        'change_reason': change_reason,
        'request_kind': request_kind,
        'before_policy': before_policy,
        'preview_policy': after_policy,
        'component_status': component_status,
        'summary': summary,
        'rollback_patch': _build_rollback_patch(before_policy),
    }


def infer_rollout_change_approval_policy(payload: Dict[str, Any]) -> Dict[str, Any]:
    prepared = normalize_rollout_change_request(payload)
    component = prepared['component']
    preview_policy = prepared['preview_policy']
    target_mode = str(preview_policy.get('rollout_mode') or '')
    canary_percent = int(preview_policy.get('canary_percent') or 0)

    if component == 'feature_engineering' and target_mode == 'native_enforced':
        return {
            'required': True,
            'mode': 'manual',
            'reason': '强制切换到 Native C++ backend 需要审批',
        }
    if component == 'feature_engineering' and target_mode == 'native_candidate':
        return {
            'required': True,
            'mode': 'manual',
            'reason': '启用 Native C++ 灰度 rollout 需要审批',
        }
    if component == 'feature_engineering' and canary_percent > 0:
        return {
            'required': True,
            'mode': 'manual',
            'reason': f'Native C++ canary 已提升到 {canary_percent}% ，需要审批',
        }
    return {'required': False, 'mode': 'auto'}


def apply_rollout_change(
    payload: Dict[str, Any],
    *,
    updated_by: str,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    prepared = normalize_rollout_change_request(payload)
    component = prepared['component']
    target_policy = dict(prepared['target_policy'])

    if prepared['change_reason'] and not str(target_policy.get('notes') or '').strip():
        target_policy['notes'] = prepared['change_reason']

    policy = ComputeRolloutService.update_policy(
        components={component: target_policy},
        updated_by=updated_by,
    )
    after_policy = deepcopy(
        next(
            (
                item
                for item in ComputeRolloutService.serialize_policy(policy).get('components', [])
                if isinstance(item, dict) and item.get('key') == component
            ),
            {},
        )
    )
    before_policy = prepared['before_policy']
    before_component_status = prepared['component_status']
    after_component_status = _get_component_runtime_status(component)

    summary = _build_summary(before_policy, after_policy or prepared['preview_policy'])
    result = {
        'component': component,
        'component_label': prepared['component_label'],
        'request_kind': prepared['request_kind'],
        'change_reason': prepared['change_reason'],
        'before_policy': before_policy,
        'after_policy': after_policy or prepared['preview_policy'],
        'requested_patch': target_policy,
        'rollback_patch': prepared['rollback_patch'],
        'before_component_status': before_component_status,
        'after_component_status': after_component_status,
        'summary': summary,
        'artifacts': [
            {
                'type': 'governance_policy',
                'name': f'{prepared["component_label"]} rollout policy',
                'uri': f'compute-rollout://{component}',
                'metadata': {
                    'component': component,
                    'request_kind': prepared['request_kind'],
                    'before_rollout_mode': before_policy.get('rollout_mode'),
                    'after_rollout_mode': (after_policy or prepared['preview_policy']).get('rollout_mode'),
                },
            }
        ],
        'metrics': {
            'governance_component': component,
            'request_kind': prepared['request_kind'],
            'previous_rollout_mode': str(before_policy.get('rollout_mode') or ''),
            'target_rollout_mode': str((after_policy or prepared['preview_policy']).get('rollout_mode') or ''),
            'target_backend': str((after_policy or prepared['preview_policy']).get('preferred_backend') or ''),
            'canary_percent': int((after_policy or prepared['preview_policy']).get('canary_percent') or 0),
            'rollback_ready': True,
            'rollout_status_before': str(before_component_status.get('rollout_status') or ''),
            'rollout_status_after': str(after_component_status.get('rollout_status') or ''),
        },
    }
    audit_details = {
        'component': component,
        'component_label': prepared['component_label'],
        'request_kind': prepared['request_kind'],
        'before_policy': before_policy,
        'after_policy': after_policy or prepared['preview_policy'],
        'before_component_status': before_component_status,
        'after_component_status': after_component_status,
        'rollback_patch': prepared['rollback_patch'],
        'change_reason': prepared['change_reason'],
    }
    return result, audit_details
