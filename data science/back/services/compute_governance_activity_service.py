"""Recent compute governance audit feed."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from services.history_service import HistoryService
from services.operation_service import OperationService

_COMPUTE_OPERATION_TYPES = {'compute_rollout_change', 'compute_benchmark'}


def _parse_timestamp(value: Any) -> datetime:
    raw = str(value or '').strip()
    if not raw:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def _component_label(component: str) -> str:
    if component == 'feature_engineering':
        return '高级特征工程'
    if component == 'scenario_simulation':
        return '批量情景模拟'
    return component or '--'


def _operation_summary(record: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(record.get('result') or {})
    metrics = dict(record.get('metrics') or {})
    input_payload = dict(record.get('input') or record.get('input_data') or {})
    operation_type = str(record.get('type') or '')
    component = str(
        result.get('component')
        or metrics.get('benchmark_component')
        or input_payload.get('component')
        or '',
    )
    component_label = str(
        result.get('component_label')
        or _component_label(component)
        or '--',
    )
    summary = str(result.get('summary') or '').strip()
    request_kind = str(result.get('request_kind') or '').strip()
    benchmark_status = ''
    rollout_mode = ''
    if operation_type == 'compute_rollout_change':
        after_policy = dict(result.get('after_policy') or {})
        target_policy = dict(input_payload.get('target_policy') or {})
        rollout_mode = str(after_policy.get('rollout_mode') or '')
        if not rollout_mode:
            rollout_mode = str(target_policy.get('rollout_mode') or '')
        if not summary:
            before_policy = dict(result.get('before_policy') or {})
            if not before_policy and target_policy:
                summary = f'目标模式 {target_policy.get("rollout_mode") or "--"}'
            else:
                summary = (
                    f'{before_policy.get("rollout_mode") or "--"} -> '
                    f'{after_policy.get("rollout_mode") or target_policy.get("rollout_mode") or "--"}'
                )
    elif operation_type == 'compute_benchmark':
        compute_metrics = dict(metrics.get('compute_metrics') or {})
        component_metrics = dict(compute_metrics.get(component) or {})
        benchmark_status = str(component_metrics.get('benchmark_status') or '').strip()
        if not summary:
            summary = str(component_metrics.get('benchmark_summary') or '').strip()

    title = (
        f'计算治理变更 · {component_label}'
        if operation_type == 'compute_rollout_change'
        else f'计算 Benchmark · {component_label}'
    )
    return {
        'entry_id': str(record.get('job_id') or ''),
        'kind': 'operation',
        'title': title,
        'status': str(record.get('status') or ''),
        'severity': 'info',
        'summary': summary,
        'created_at': str(record.get('submitted_at') or ''),
        'component': component,
        'component_label': component_label,
        'operation_id': str(record.get('job_id') or ''),
        'operation_type': operation_type,
        'request_kind': request_kind,
        'benchmark_status': benchmark_status,
        'rollout_mode': rollout_mode,
    }


def _history_summary(record: Dict[str, Any]) -> Dict[str, Any]:
    details = dict(record.get('details') or {})
    component = str(details.get('component') or '')
    component_label = _component_label(component)
    summary = str(
        details.get('reason')
        or details.get('summary')
        or details.get('message')
        or '',
    ).strip()
    if not summary:
        failure_count = int(details.get('recent_failure_count') or 0)
        failure_threshold = int(details.get('failure_threshold') or 0)
        if failure_count and failure_threshold:
            summary = f'Native 失败 {failure_count}/{failure_threshold}'
    return {
        'entry_id': str(record.get('id') or ''),
        'kind': 'system_event',
        'title': str(record.get('title') or '计算治理事件'),
        'status': str(record.get('status') or ''),
        'severity': str(record.get('severity') or 'warning'),
        'summary': summary,
        'created_at': str(record.get('created_at') or ''),
        'component': component,
        'component_label': component_label,
        'operation_id': str(details.get('operation_id') or ''),
        'operation_type': 'system_event',
        'request_kind': str(record.get('action') or ''),
        'benchmark_status': '',
        'rollout_mode': str(details.get('rolled_back_to') or ''),
    }


class ComputeGovernanceActivityService:
    """Merge recent governance operations with system guard events."""

    @classmethod
    def list_recent_activity(
        cls,
        uid: str,
        *,
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        try:
            operations = OperationService.list_operations(
                uid,
                limit=max(limit * 2, 12),
                scope='control_plane',
            )
        except Exception:
            operations = []
        operation_entries = [
            _operation_summary(record)
            for record in operations
            if str(record.get('type') or '') in _COMPUTE_OPERATION_TYPES
        ]

        system_events = HistoryService.get_recent_activity(
            'system',
            limit=max(limit, 6),
            activity_type='compute_governance',
        )
        history_entries = [
            _history_summary(record)
            for record in system_events
            if str(record.get('action') or '').startswith('compute_rollout_')
        ]

        merged = [
            entry
            for entry in (operation_entries + history_entries)
            if entry.get('component') or entry.get('kind') == 'system_event'
        ]
        merged.sort(
            key=lambda item: _parse_timestamp(item.get('created_at')),
            reverse=True,
        )
        return merged[:limit]
