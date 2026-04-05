"""Internal operation dispatch runtime helpers.

This module keeps request-facing dispatch bootstrap separate from the
operation state machine so API routes stay small and the operation service
does not own thread timing concerns.
"""

from __future__ import annotations

import time
from typing import Callable

from services.operation_dispatcher import spawn_operation_worker

STARTUP_READY_STATUSES = {'running', 'failed', 'cancelled', 'succeeded'}
STARTUP_WAIT_TIMEOUT_S = 2.5
STARTUP_POLL_INTERVAL_S = 0.2


def start_internal_operation_dispatch(
    app,
    operation_id: str,
    *,
    process_callback: Callable[[str], None],
    fetch_callback: Callable[[str], dict | None],
    startup_timeout_s: float = STARTUP_WAIT_TIMEOUT_S,
    poll_interval_s: float = STARTUP_POLL_INTERVAL_S,
) -> dict:
    """Start internal dispatch and fall back inline if startup stalls.

    The background worker remains the default path. If the operation is still
    queued/dispatching after a short window, the current request thread also
    attempts dispatch. The operation service is responsible for making the
    execution start idempotent.
    """

    spawn_operation_worker(
        app,
        operation_id,
        process_callback,
    )

    if _wait_for_operation_start(
        operation_id,
        fetch_callback=fetch_callback,
        timeout_s=startup_timeout_s,
        poll_interval_s=poll_interval_s,
    ):
        return {
            'operation_id': operation_id,
            'status': 'accepted',
            'dispatch_mode': 'background',
        }

    with app.app_context():
        process_callback(operation_id)

    return {
        'operation_id': operation_id,
        'status': 'accepted',
        'dispatch_mode': 'inline_fallback',
    }


def _wait_for_operation_start(
    operation_id: str,
    *,
    fetch_callback: Callable[[str], dict | None],
    timeout_s: float,
    poll_interval_s: float,
) -> bool:
    deadline = time.monotonic() + max(timeout_s, 0.2)
    interval = max(poll_interval_s, 0.05)

    while time.monotonic() < deadline:
        record = fetch_callback(operation_id) or {}
        status = str(record.get('status') or '').strip().lower()
        if status in STARTUP_READY_STATUSES:
            return True
        if status not in {'queued', 'dispatching', ''}:
            return True
        time.sleep(interval)
    return False
