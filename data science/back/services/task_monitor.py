"""
Task monitor adapter.

This module now reads from the unified operations model instead of maintaining
an independent execution log. The write methods are kept only as a temporary
compatibility bridge.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional

from services.control_task_service import ControlTaskService
from services.operation_service import OperationService

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""

    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TaskMonitor:
    """Read-only oriented adapter over the unified operation store."""

    def __init__(self):
        self._compat_operations: Dict[str, str] = {}

    def record_task_start(self, task_name: str, metadata: Dict = None) -> Optional[str]:
        logger.warning('TaskMonitor.record_task_start is deprecated; creating compatibility operation for %s', task_name)
        control_task = ControlTaskService.ensure_control_task(
            control_task_id=f'{task_name}_compat',
            kind='scheduler',
            operation_type=task_name,
            title=f'Compatibility task monitor for {task_name}',
            schedule=None,
            default_input=metadata or {},
        )
        operation = OperationService.create_operation(
            'system',
            task_name,
            metadata or {},
            control_task_id=control_task['id'],
            trigger='compat',
        )
        operation_id = operation['job_id']
        self._compat_operations[operation_id] = task_name
        OperationService.mark_running(operation_id, message=f'Compatibility monitor started {task_name}')
        return operation_id

    def record_task_end(
        self,
        execution_id: str,
        status: TaskStatus,
        error_message: str = None,
        result_metadata: Dict = None,
    ):
        if not execution_id:
            return
        if status == TaskStatus.SUCCESS:
            OperationService.mark_succeeded(
                execution_id,
                result_metadata or {'task_name': self._compat_operations.get(execution_id)},
                message='Compatibility monitor completed',
            )
            return
        if status == TaskStatus.STARTED:
            OperationService.mark_running(execution_id, message='Compatibility monitor marked started')
            return
        if status == TaskStatus.TIMEOUT:
            OperationService.mark_failed(execution_id, code='TASK_TIMEOUT', message=error_message or 'Task timed out')
            return
        OperationService.mark_failed(execution_id, code='TASK_FAILED', message=error_message or 'Task failed')

    def get_recent_executions(self, task_name: str = None, limit: int = 10) -> list:
        operations = OperationService.list_operations(
            'system',
            operation_type=task_name,
            limit=max(limit, 1),
        )
        items = []
        for operation in operations[:limit]:
            items.append(
                {
                    'id': operation.get('job_id'),
                    'task_name': operation.get('type'),
                    'status': operation.get('status'),
                    'started_at': operation.get('started_at'),
                    'ended_at': operation.get('completed_at'),
                    'duration_seconds': _duration_seconds(
                        operation.get('started_at'),
                        operation.get('completed_at'),
                    ),
                    'metadata': operation.get('input') or {},
                    'result_metadata': operation.get('metrics') or {},
                    'error_message': (operation.get('error') or {}).get('message'),
                    'environment': 'gae',
                }
            )
        return items

    def get_task_stats(self, task_name: str, days: int = 7) -> Dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        operations = OperationService.list_operations('system', operation_type=task_name, limit=200)
        filtered = [
            item for item in operations
            if (OperationService._coerce_datetime(item.get('submitted_at')) or cutoff) >= cutoff
        ]
        total = len(filtered)
        success = sum(1 for item in filtered if item.get('status') == 'succeeded')
        failed = sum(1 for item in filtered if item.get('status') == 'failed')
        durations = [
            _duration_seconds(item.get('started_at'), item.get('completed_at'))
            for item in filtered
        ]
        valid_durations = [duration for duration in durations if duration is not None]
        return {
            'task_name': task_name,
            'period_days': days,
            'total_executions': total,
            'success_count': success,
            'failed_count': failed,
            'success_rate': (success / total * 100) if total > 0 else 0,
            'avg_duration_seconds': (sum(valid_durations) / len(valid_durations)) if valid_durations else 0,
        }


def _duration_seconds(started_at: Any, ended_at: Any) -> Optional[float]:
    start_dt = OperationService._coerce_datetime(started_at)
    end_dt = OperationService._coerce_datetime(ended_at)
    if not start_dt or not end_dt:
        return None
    return round((end_dt - start_dt).total_seconds(), 2)


_task_monitor = None


def get_task_monitor() -> TaskMonitor:
    """获取任务监控器单例"""

    global _task_monitor
    if _task_monitor is None:
        _task_monitor = TaskMonitor()
    return _task_monitor
