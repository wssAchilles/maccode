"""Projection helpers for control-task records."""

from __future__ import annotations

from typing import Any, Dict, Optional

from services.operation_projection import coerce_datetime


def _as_iso(value: Any) -> Optional[str]:
    dt = coerce_datetime(value)
    if dt is not None:
        return dt.isoformat()
    if isinstance(value, str) and value:
        return value
    return None


def serialize_control_task(
    record: Dict[str, Any],
    *,
    control_task_id: Optional[str] = None,
) -> Dict[str, Any]:
    payload = dict(record or {})
    if control_task_id is not None and not payload.get('id'):
        payload['id'] = control_task_id

    return {
        'id': str(payload.get('id') or control_task_id or ''),
        'kind': str(payload.get('kind') or ''),
        'operation_type': str(
            payload.get('operation_type')
            or payload.get('default_input', {}).get('operation_type')
            or payload.get('default_input', {}).get('task_name')
            or '',
        ),
        'title': str(payload.get('title') or ''),
        'schedule': payload.get('schedule'),
        'default_input': dict(payload.get('default_input') or {}),
        'dependencies': list(payload.get('dependencies') or []),
        'approval_policy': dict(payload.get('approval_policy') or {}),
        'enabled': bool(payload.get('enabled', True)),
        'owner': str(payload.get('owner') or ''),
        'created_at': _as_iso(payload.get('created_at')),
        'updated_at': _as_iso(payload.get('updated_at')),
    }
