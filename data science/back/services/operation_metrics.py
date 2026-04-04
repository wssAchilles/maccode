"""Operation metric normalization helpers.

Keeps compute/runtime metric shaping out of the main operation service so
state transitions stay focused on orchestration.
"""

from __future__ import annotations

from typing import Any, Dict


_COMPUTE_COMPONENT_LABELS = {
    'feature_engineering': '高级特征工程',
    'scenario_simulation': '批量情景模拟',
}


def normalize_compute_metrics(payload: Any) -> Dict[str, Dict[str, Any]]:
    """Extract compute component metrics from loosely structured payloads."""

    candidate = _find_compute_metrics_payload(payload)
    if not candidate:
        return {}

    normalized: Dict[str, Dict[str, Any]] = {}
    for component, raw_metrics in candidate.items():
        if not isinstance(raw_metrics, dict):
            continue
        duration_ms = _as_float(raw_metrics.get('duration_ms'))
        if duration_ms is None:
            duration_ms = _as_float(raw_metrics.get('last_duration_ms'))
        rows = _as_int(raw_metrics.get('input_rows'))
        if rows is None:
            rows = _as_int(raw_metrics.get('rows'))
        if rows is None:
            rows = _as_int(raw_metrics.get('last_rows'))
        normalized[component] = {
            'key': component,
            'label': _COMPUTE_COMPONENT_LABELS.get(
                component,
                str(raw_metrics.get('label') or component.replace('_', ' ').title()),
            ),
            'backend': str(
                raw_metrics.get('backend')
                or raw_metrics.get('active_backend')
                or raw_metrics.get('preferred_backend')
                or 'python_pandas'
            ),
            'duration_ms': round(float(duration_ms or 0.0), 3),
            'rows': int(rows or 0),
            'context': str(
                raw_metrics.get('context')
                or raw_metrics.get('last_context')
                or ''
            ),
            'native_enabled': bool(raw_metrics.get('native_enabled')),
            'native_available': bool(raw_metrics.get('native_available')),
            'module_name': str(raw_metrics.get('module_name') or ''),
            'fallback_reason': str(raw_metrics.get('fallback_reason') or ''),
            'rollout_mode': str(raw_metrics.get('rollout_mode') or ''),
            'rollout_reason': str(raw_metrics.get('rollout_reason') or ''),
            'benchmark_ready': bool(raw_metrics.get('benchmark_ready')),
        }
    return normalized


def extract_operation_metrics(result: Dict[str, Any]) -> Dict[str, Any]:
    """Build a compact operation-level metric payload from a result dict."""

    if not isinstance(result, dict):
        return {}

    merged: Dict[str, Any] = {}
    for key in ('performance', 'metrics'):
        candidate = result.get(key)
        if isinstance(candidate, dict):
            merged = merge_operation_metrics(merged, candidate)

    direct_compute = normalize_compute_metrics(result)
    if direct_compute:
        merged = merge_operation_metrics(
            merged,
            {'compute_metrics': direct_compute},
        )
    return merged


def merge_operation_metrics(
    existing: Dict[str, Any] | None,
    incoming: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """Merge scalar metrics and nested compute metrics safely."""

    merged: Dict[str, Any] = dict(existing or {})
    if not isinstance(incoming, dict):
        return merged

    for key, value in incoming.items():
        if key == 'compute_metrics':
            continue
        sanitized = _sanitize_metric_value(value)
        if sanitized is not None:
            merged[key] = sanitized

    compute_metrics = normalize_compute_metrics(incoming)
    if compute_metrics:
        existing_compute = merged.get('compute_metrics')
        current_compute = dict(existing_compute) if isinstance(existing_compute, dict) else {}
        for component, component_metrics in compute_metrics.items():
            current = current_compute.get(component)
            if isinstance(current, dict):
                current_compute[component] = {
                    **current,
                    **component_metrics,
                }
            else:
                current_compute[component] = component_metrics
        merged['compute_metrics'] = current_compute

    return merged


def attach_step_metrics(
    step: Dict[str, Any],
    metrics: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """Attach normalized metrics to a step summary."""

    if not isinstance(step, dict):
        return {}
    merged_metrics = merge_operation_metrics(step.get('metrics'), metrics or {})
    if not merged_metrics:
        return dict(step)
    return {
        **step,
        'metrics': merged_metrics,
    }


def _find_compute_metrics_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    direct_components = {
        key: value
        for key, value in payload.items()
        if key in _COMPUTE_COMPONENT_LABELS and isinstance(value, dict)
    }
    if direct_components:
        return direct_components

    candidate = payload.get('compute_metrics')
    if isinstance(candidate, dict):
        return candidate

    for key in ('metrics', 'performance', 'result', 'output'):
        nested = payload.get(key)
        normalized = _find_compute_metrics_payload(nested)
        if normalized:
            return normalized
    return {}


def _sanitize_metric_value(value: Any) -> Any | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, str):
        return value[:120]
    return None


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return None
    return None
