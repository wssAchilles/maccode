"""Dependency-state helpers for control-task runtime governance."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


def build_task_index(tasks: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for task in tasks:
        task_id = str(task.get('id') or '').strip()
        if task_id:
            index[task_id] = task
    return index


def evaluate_dependency_state(
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
        dependency = tasks_by_id.get(str(dependency_id).strip())
        if dependency is None:
            has_missing = True
            details.append(
                {
                    'id': str(dependency_id),
                    'state': 'missing',
                    'title': str(dependency_id),
                }
            )
            continue

        enabled = bool(dependency.get('enabled'))
        state = 'ready' if enabled else 'paused'
        if not enabled:
            has_blocked = True
        details.append(
            {
                'id': str(dependency.get('id') or dependency_id),
                'state': state,
                'title': str(dependency.get('title') or dependency_id),
            }
        )

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
