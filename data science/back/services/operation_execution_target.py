"""Execution target routing rules for operations.

Keeps worker selection policy out of the main operation service so orchestration
state remains focused on persistence and transitions.
"""

from __future__ import annotations

from typing import Any, Dict


def resolve_operation_execution_target(
    operation_type: str,
    payload: Dict[str, Any] | None = None,
    metadata: Dict[str, Any] | None = None,
) -> str:
    payload = dict(payload or {})
    metadata = dict(metadata or {})

    explicit_target = str(
        payload.get('execution_target')
        or metadata.get('execution_target')
        or '',
    ).strip()
    if explicit_target in {'light_worker', 'heavy_worker'}:
        return explicit_target

    if operation_type in {'ml_train', 'rag_ingest'}:
        return 'heavy_worker'

    if operation_type == 'compute_benchmark':
        component = str(payload.get('component') or '').strip()
        if component == 'feature_engineering':
            return 'heavy_worker'
        return 'light_worker'

    return 'light_worker'


def resolve_step_execution_target(
    operation_target: str,
    tool_target: str | None,
) -> str | None:
    tool_target = str(tool_target or '').strip()
    if tool_target in {'operation_target', 'dynamic_worker'}:
        return operation_target or 'light_worker'
    return tool_target or operation_target or None
