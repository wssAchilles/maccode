"""Bridge planning-layer control tasks into executable operations."""

from __future__ import annotations

from typing import Any, Dict, Optional

from services.control_task_service import ControlTaskService
from services.operation_service import OperationService


class ControlTaskNotFoundError(ValueError):
    """Raised when a requested control task does not exist."""


class ControlTaskDisabledError(ValueError):
    """Raised when a control task is paused and cannot be triggered."""


class ControlTaskConfigurationError(ValueError):
    """Raised when a control task does not contain enough execution metadata."""


def _resolve_operation_type(task: Dict[str, Any]) -> str:
    operation_type = str(
        task.get('operation_type')
        or task.get('default_input', {}).get('operation_type')
        or task.get('default_input', {}).get('task_name')
        or '',
    ).strip()
    if not operation_type:
        raise ControlTaskConfigurationError('规划任务缺少 operation_type，无法触发运行')
    return operation_type


def run_control_task(
    *,
    uid: str,
    control_task_id: str,
    input_overrides: Optional[Dict[str, Any]] = None,
    trigger: str = 'manual',
) -> Dict[str, Any]:
    task = ControlTaskService.get_control_task(control_task_id)
    if not task:
        raise ControlTaskNotFoundError('规划任务不存在')
    if not bool(task.get('enabled', True)):
        raise ControlTaskDisabledError('规划任务已暂停，无法触发运行')

    payload = dict(task.get('default_input') or {})
    payload.update(input_overrides or {})
    operation_type = _resolve_operation_type(task)

    return OperationService.create_operation(
        uid,
        operation_type,
        payload,
        control_task_id=control_task_id,
        trigger=trigger,
        approval_policy=dict(task.get('approval_policy') or {}),
        metadata={
            'control_task_run': True,
            'control_task_kind': task.get('kind'),
        },
    )
