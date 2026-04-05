"""Helpers for projecting compute runtime and governance events."""

from __future__ import annotations

from typing import Any, Dict, List

from services.operation_metrics import normalize_compute_metrics
from services.operation_projection import build_event


def _backend_label(value: str) -> str:
    mapping = {
        'python_pandas': 'Python Pandas',
        'python_vectorized': 'Python Vectorized',
        'python_loop': 'Python Loop',
        'native_cpp': 'Native C++',
    }
    return mapping.get(value, value or '--')


def build_compute_runtime_events(
    previous_metrics: Dict[str, Any] | None,
    incoming_metrics: Dict[str, Any] | None,
    *,
    phase: str,
    progress: int,
) -> List[Dict[str, Any]]:
    previous = normalize_compute_metrics(previous_metrics or {})
    current = normalize_compute_metrics(incoming_metrics or {})
    if not current:
        return []

    events: List[Dict[str, Any]] = []
    for component, payload in current.items():
        prior = previous.get(component) or {}
        label = str(payload.get('label') or component)
        backend = str(payload.get('backend') or 'python_pandas')
        rollout_mode = str(payload.get('rollout_mode') or '')
        rollout_reason = str(payload.get('rollout_reason') or '').strip()
        fallback_reason = str(payload.get('fallback_reason') or '').strip()
        context = str(payload.get('context') or '').strip()
        auto_rollback_applied = bool(payload.get('guard_auto_rollback_applied'))
        auto_rollback_reason = str(
            payload.get('guard_last_auto_rollback_reason') or '',
        ).strip()
        auto_rollback_at = str(payload.get('guard_last_auto_rollback_at') or '').strip()
        recent_failure_count = int(payload.get('guard_recent_failure_count') or 0)
        previous_failure_count = int(prior.get('guard_recent_failure_count') or 0)
        failure_threshold = int(payload.get('guard_failure_threshold') or 0)
        guard_window_minutes = int(payload.get('guard_window_minutes') or 0)
        benchmark_status = str(payload.get('benchmark_status') or '').strip()
        previous_benchmark_status = str(prior.get('benchmark_status') or '').strip()
        benchmark_summary = str(payload.get('benchmark_summary') or '').strip()
        benchmark_speedup = payload.get('benchmark_speedup_ratio')

        selection_changed = any(
            str(prior.get(key) or '') != str(payload.get(key) or '')
            for key in ('backend', 'rollout_mode', 'rollout_reason', 'context')
        )
        if selection_changed:
            message = f'{label} 选择 {_backend_label(backend)}'
            if rollout_mode:
                message += f' · {rollout_mode}'
            if rollout_reason:
                message += f' · {rollout_reason}'
            if context:
                message += f' · {context}'
            events.append(
                build_event(
                    event_type='compute.backend_selected',
                    phase=phase,
                    status='running',
                    message=message,
                    progress=progress,
                    extra={
                        'metrics': {
                            'compute_metrics': {
                                component: payload,
                            }
                        }
                    },
                )
            )

        if fallback_reason and fallback_reason != str(prior.get('fallback_reason') or '').strip():
            events.append(
                build_event(
                    event_type='compute.fallback',
                    phase=phase,
                    status='running',
                    message=f'{label} 回退到 Python 路径 · {fallback_reason}',
                    progress=progress,
                    extra={
                        'metrics': {
                            'compute_metrics': {
                                component: payload,
                            }
                        }
                    },
                )
            )

        if recent_failure_count > previous_failure_count:
            message = f'{label} Native failure 已记录'
            if guard_window_minutes and failure_threshold:
                message += (
                    f' · {guard_window_minutes} 分钟窗口内 {recent_failure_count}/'
                    f'{failure_threshold}'
                )
            if fallback_reason:
                message += f' · {fallback_reason}'
            events.append(
                build_event(
                    event_type='compute.guard_failure',
                    phase=phase,
                    status='running',
                    message=message,
                    progress=progress,
                    extra={
                        'metrics': {
                            'compute_metrics': {
                                component: payload,
                            }
                        }
                    },
                )
            )

        if benchmark_status and benchmark_status != previous_benchmark_status:
            if benchmark_status == 'passed':
                message = f'{label} benchmark 准入通过'
                if benchmark_speedup is not None:
                    try:
                        message += f' · {float(benchmark_speedup):.2f}x'
                    except Exception:
                        pass
                event_status = 'succeeded'
            elif benchmark_status == 'failed':
                message = f'{label} benchmark 准入未通过'
                if benchmark_summary:
                    message += f' · {benchmark_summary}'
                event_status = 'failed'
            elif benchmark_status == 'stale':
                message = f'{label} benchmark 证据已过期'
                if benchmark_summary:
                    message += f' · {benchmark_summary}'
                event_status = 'running'
            elif benchmark_status == 'recorded':
                message = f'{label} benchmark 样本已记录，等待受控准入'
                event_status = 'running'
            else:
                message = f'{label} benchmark 状态更新为 {benchmark_status}'
                if benchmark_summary:
                    message += f' · {benchmark_summary}'
                event_status = 'running'
            events.append(
                build_event(
                    event_type='compute.benchmark_gate',
                    phase=phase,
                    status=event_status,
                    message=message,
                    progress=progress,
                    extra={
                        'metrics': {
                            'compute_metrics': {
                                component: payload,
                            }
                        }
                    },
                )
            )

        if auto_rollback_applied and auto_rollback_at != str(prior.get('guard_last_auto_rollback_at') or '').strip():
            message = f'{label} 触发自动回退到稳定 Python'
            if recent_failure_count and failure_threshold and guard_window_minutes:
                message += (
                    f' · {guard_window_minutes} 分钟内 {recent_failure_count}/'
                    f'{failure_threshold} 次 Native 失败'
                )
            if auto_rollback_reason:
                message += f' · {auto_rollback_reason}'
            events.append(
                build_event(
                    event_type='compute.auto_rollback',
                    phase=phase,
                    status='running',
                    message=message,
                    progress=progress,
                    extra={
                        'metrics': {
                            'compute_metrics': {
                                component: payload,
                            }
                        }
                    },
                )
            )
    return events


def build_compute_rollout_change_event(
    result: Dict[str, Any] | None,
    *,
    progress: int = 100,
) -> Dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    before_policy = result.get('before_policy')
    after_policy = result.get('after_policy')
    if not isinstance(before_policy, dict) or not isinstance(after_policy, dict):
        return None

    label = str(result.get('component_label') or result.get('component') or '计算治理')
    request_kind = str(result.get('request_kind') or '')
    before_mode = str(before_policy.get('rollout_mode') or '--')
    after_mode = str(after_policy.get('rollout_mode') or '--')
    canary = int(after_policy.get('canary_percent') or 0)
    if request_kind == 'rollback':
        message = f'{label} 已回退到 {after_mode}'
    else:
        message = f'{label} rollout 已从 {before_mode} 切换到 {after_mode}'
    if canary > 0:
        message += f' · canary {canary}%'
    return build_event(
        event_type='compute.rollout_applied',
        phase='compute_rollout_apply',
        status='succeeded',
        message=message,
        progress=progress,
        extra={
            'metrics': {
                'rollout_component': str(result.get('component') or ''),
                'previous_rollout_mode': before_mode,
                'target_rollout_mode': after_mode,
                'canary_percent': canary,
            }
        },
    )
