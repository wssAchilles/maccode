"""Runtime enrichment for control-task planning records."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from config import Config
from services.control_task_validation import normalize_schedule
from services.operation_projection import coerce_datetime, serialize_operation


def _jobs_collection(client):
    return client.collection(Config.JOBS_COLLECTION)


def _control_tasks_collection(client):
    return client.collection(getattr(Config, 'CONTROL_TASKS_COLLECTION', 'control_tasks'))


def _parse_schedule_next_run(schedule: Optional[str], *, now: Optional[datetime] = None) -> Optional[str]:
    if not schedule:
        return None
    normalized = normalize_schedule(schedule)
    if normalized is None:
        return None

    current = now or datetime.now(timezone.utc)
    lowered = normalized.lower()
    if lowered.startswith('every ') and lowered.endswith(' hours'):
        interval = int(lowered.split()[1])
        next_time = current + timedelta(hours=interval)
        return next_time.isoformat()

    if lowered.startswith('every day '):
        time_text = lowered.replace('every day ', '').replace(' utc', '')
        hour_text, minute_text = time_text.split(':', 1)
        candidate = current.replace(
            hour=int(hour_text),
            minute=int(minute_text),
            second=0,
            microsecond=0,
        )
        if candidate <= current:
            candidate += timedelta(days=1)
        return candidate.isoformat()

    return None


def _latest_operations_by_control_task(client) -> Dict[str, Dict[str, Any]]:
    snapshots = _jobs_collection(client).stream()
    latest: Dict[str, Dict[str, Any]] = {}
    for snapshot in snapshots:
        record = snapshot.to_dict() or {}
        control_task_id = str(record.get('control_task_id') or '').strip()
        if not control_task_id:
            continue
        submitted_at = coerce_datetime(record.get('submitted_at')) or datetime.min.replace(tzinfo=timezone.utc)
        current = latest.get(control_task_id)
        current_submitted = coerce_datetime(current.get('submitted_at')) if current else None
        if current is None or (current_submitted or datetime.min.replace(tzinfo=timezone.utc)) <= submitted_at:
            latest[control_task_id] = record
    return latest


def _dependency_details(
    task: Dict[str, Any],
    *,
    tasks_by_id: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    dependencies = list(task.get('dependencies') or [])
    if not dependencies:
        return {
            'dependency_state': 'none',
            'dependency_summary': '无依赖',
            'dependency_details': [],
        }

    details: List[Dict[str, Any]] = []
    has_missing = False
    has_blocked = False
    for dependency_id in dependencies:
        dependency = tasks_by_id.get(dependency_id)
        if dependency is None:
            has_missing = True
            details.append({
                'id': dependency_id,
                'state': 'missing',
                'title': dependency_id,
            })
            continue

        enabled = bool(dependency.get('enabled'))
        state = 'ready' if enabled else 'paused'
        if not enabled:
            has_blocked = True
        details.append({
            'id': dependency_id,
            'state': state,
            'title': dependency.get('title') or dependency_id,
        })

    if has_missing:
        summary = '存在未定义依赖'
        state = 'missing'
    elif has_blocked:
        summary = '存在已暂停依赖'
        state = 'blocked'
    else:
        summary = '依赖已就绪'
        state = 'ready'

    return {
        'dependency_state': state,
        'dependency_summary': summary,
        'dependency_details': details,
    }


def enrich_control_tasks(
    client,
    tasks: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    raw_tasks = list(tasks)
    tasks_by_id = {str(task.get('id') or ''): task for task in raw_tasks}
    latest_operations = _latest_operations_by_control_task(client)
    enriched: List[Dict[str, Any]] = []
    for task in raw_tasks:
        task_id = str(task.get('id') or '')
        runtime = _dependency_details(task, tasks_by_id=tasks_by_id)
        latest_operation = latest_operations.get(task_id)
        enriched.append(
            {
                **task,
                'next_run_at': _parse_schedule_next_run(task.get('schedule')),
                'latest_operation': serialize_operation(latest_operation) if latest_operation else None,
                **runtime,
            }
        )
    return enriched
