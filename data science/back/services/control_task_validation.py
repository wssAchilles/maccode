"""Validation helpers for control-task definitions."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional


class ControlTaskValidationError(ValueError):
    """Raised when a control-task definition contains invalid values."""


_HOURLY_SCHEDULE_PATTERN = re.compile(r'^every\s+([1-9]\d*)\s+hours?$', re.IGNORECASE)
_DAILY_SCHEDULE_PATTERN = re.compile(
    r'^every\s+day\s+([01]\d|2[0-3]):([0-5]\d)(?:\s+UTC)?$',
    re.IGNORECASE,
)
_DEPENDENCY_PATTERN = re.compile(r'^[A-Za-z][A-Za-z0-9_:-]{0,63}$')


def normalize_schedule(value: Any) -> Optional[str]:
    normalized = str(value).strip() if value is not None else ''
    if normalized == '' or normalized.lower() == 'manual':
        return None

    hourly_match = _HOURLY_SCHEDULE_PATTERN.fullmatch(normalized)
    if hourly_match:
        return f"every {int(hourly_match.group(1))} hours"

    daily_match = _DAILY_SCHEDULE_PATTERN.fullmatch(normalized)
    if daily_match:
        return f"every day {daily_match.group(1)}:{daily_match.group(2)} UTC"

    raise ControlTaskValidationError(
        '调度策略格式无效，仅支持留空、manual、every N hours、every day HH:MM UTC',
    )


def normalize_owner(value: Any) -> str:
    return str(value or '').strip() or 'system'


def normalize_dependencies(value: Optional[Iterable[Any]]) -> List[str]:
    if not value:
        return []

    normalized: List[str] = []
    seen = set()
    items = value if isinstance(value, (list, tuple, set)) else [value]
    for item in items:
        label = str(item or '').strip()
        if not label:
            continue
        if not _DEPENDENCY_PATTERN.fullmatch(label):
            raise ControlTaskValidationError(
                '依赖标识只能包含字母、数字、下划线、短横线、冒号，且必须以字母开头',
            )
        if label in seen:
            raise ControlTaskValidationError(f'依赖标识重复: {label}')
        seen.add(label)
        normalized.append(label)
    return normalized


def normalize_approval_policy(value: Dict[str, Any]) -> Dict[str, Any]:
    policy = dict(value or {})
    required = bool(policy.get('required'))
    mode = str(
        policy.get('mode') or ('manual' if required else 'auto'),
    ).strip().lower()
    if mode not in {'auto', 'manual'}:
        mode = 'manual' if required else 'auto'

    reason = str(policy.get('reason') or '').strip() or None
    normalized = {
        'required': required,
        'mode': mode,
    }
    if reason is not None:
        normalized['reason'] = reason
    return normalized
