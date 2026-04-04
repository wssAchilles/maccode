"""SSE helpers for operation event streaming."""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, Iterable, Optional


TERMINAL_STATUSES = {'succeeded', 'failed', 'cancelled'}


def format_sse(
    data: Dict[str, Any],
    *,
    event: str,
    event_id: Optional[str] = None,
) -> str:
    lines = [f'event: {event}']
    if event_id is not None:
        lines.append(f'id: {event_id}')
    payload = json.dumps(data, ensure_ascii=False)
    for line in payload.splitlines() or ['{}']:
        lines.append(f'data: {line}')
    lines.append('')
    return '\n'.join(lines) + '\n'


def format_keepalive() -> str:
    return ': keep-alive\n\n'


def stream_operation_events(
    *,
    operation_id: str,
    fetch_operation: Callable[[], Optional[Dict[str, Any]]],
    list_events: Callable[[], Iterable[Dict[str, Any]]],
    poll_interval_s: float = 2.0,
    max_duration_s: float = 55.0,
) -> Iterable[str]:
    started = time.monotonic()
    cursor = 0
    last_status = None
    last_progress = None
    last_step = ''
    last_cancel_requested = None
    last_approval_state = ''
    last_metrics = ''
    state_seq = 0

    operation = fetch_operation()
    if operation is None:
        yield format_sse(
            {
                'operation_id': operation_id,
                'error': {
                    'code': 'OPERATION_NOT_FOUND',
                    'message': '任务不存在',
                },
            },
            event='operation.error',
            event_id='error-0',
        )
        return

    yield format_sse(
        operation,
        event='operation.snapshot',
        event_id='snapshot-0',
    )
    last_status = operation.get('status')
    last_progress = operation.get('progress')
    last_step = json.dumps(operation.get('current_step') or {}, ensure_ascii=False, sort_keys=True)
    last_cancel_requested = bool(operation.get('cancel_requested', False))
    last_approval_state = json.dumps(
        operation.get('approval_state') or {},
        ensure_ascii=False,
        sort_keys=True,
    )
    last_metrics = json.dumps(operation.get('metrics') or {}, ensure_ascii=False, sort_keys=True)

    while time.monotonic() - started < max_duration_s:
        operation = fetch_operation()
        if operation is None:
            yield format_sse(
                {
                    'operation_id': operation_id,
                    'error': {
                        'code': 'OPERATION_NOT_FOUND',
                        'message': '任务不存在',
                    },
                },
                event='operation.error',
                event_id='error-disappeared',
            )
            return

        events = list(list_events())
        if cursor < len(events):
            for index, event in enumerate(events[cursor:], start=cursor + 1):
                yield format_sse(
                    event,
                    event=event.get('type', 'operation.event'),
                    event_id=f'event-{index}',
                )
            cursor = len(events)
        else:
            yield format_keepalive()

        status = operation.get('status')
        progress = operation.get('progress')
        current_step = operation.get('current_step')
        cancel_requested = bool(operation.get('cancel_requested', False))
        approval_state = operation.get('approval_state')
        metrics = operation.get('metrics') or {}
        current_step_key = json.dumps(current_step or {}, ensure_ascii=False, sort_keys=True)
        approval_state_key = json.dumps(approval_state or {}, ensure_ascii=False, sort_keys=True)
        metrics_key = json.dumps(metrics, ensure_ascii=False, sort_keys=True)
        if (
            status != last_status
            or progress != last_progress
            or current_step_key != last_step
            or cancel_requested != last_cancel_requested
            or approval_state_key != last_approval_state
            or metrics_key != last_metrics
        ):
            state_seq += 1
            yield format_sse(
                {
                    'operation_id': operation_id,
                    'status': status,
                    'progress': progress,
                    'current_step': current_step,
                    'cancel_requested': cancel_requested,
                    'approval_state': approval_state,
                    'metrics': metrics,
                },
                event='operation.state',
                event_id=f'state-{state_seq}',
            )
            last_status = status
            last_progress = progress
            last_step = current_step_key
            last_cancel_requested = cancel_requested
            last_approval_state = approval_state_key
            last_metrics = metrics_key

        if status in TERMINAL_STATUSES:
            yield format_sse(
                {
                    'operation_id': operation_id,
                    'status': status,
                    'metrics': operation.get('metrics') or {},
                },
                event='operation.closed',
                event_id='closed',
            )
            return

        time.sleep(poll_interval_s)
