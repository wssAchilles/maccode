"""Dispatch boundary for operation execution.

This module owns Cloud Tasks enqueueing and local thread fallback so the
operation service can focus on state transitions and persistence.
"""

from __future__ import annotations

import logging
import threading
import urllib.error
import urllib.request
from typing import Callable

logger = logging.getLogger(__name__)


def dispatch_operation(
    app,
    operation_id: str,
    operation_type: str,
    *,
    execute_callback: Callable[[str], None],
) -> None:
    if enqueue_orchestrator_dispatch(app, operation_id, operation_type):
        return

    mode = (app.config.get('TASKS_EXECUTION_MODE') or 'inline').lower()
    if mode == 'cloud_tasks' and enqueue_cloud_task(app, operation_id, operation_type):
        return

    spawn_operation_worker(app, operation_id, execute_callback)


def enqueue_cloud_task(app, operation_id: str, operation_type: str) -> bool:
    try:
        from google.cloud import tasks_v2
    except ImportError:
        logger.warning('google-cloud-tasks unavailable, falling back to inline execution')
        return False

    try:
        client = tasks_v2.CloudTasksClient()
        project = app.config.get('GCP_PROJECT_ID')
        location = app.config.get('TASKS_LOCATION')
        queue = app.config.get('TASKS_QUEUE_NAME')
        queue_path = client.queue_path(project, location, queue)
        url = build_dispatch_url(app, operation_id)
        task = {
            'http_request': {
                'http_method': tasks_v2.HttpMethod.POST,
                'url': url,
                'headers': {
                    'Content-Type': 'application/json',
                    'X-Internal-Job-Token': app.config.get(
                        'INTERNAL_JOB_TOKEN',
                        'dev-internal-job-token',
                    ),
                },
                'body': b'{}',
            }
        }
        client.create_task(parent=queue_path, task=task)
        logger.info(
            'Enqueued Cloud Task for operation %s (%s) via %s',
            operation_id,
            operation_type,
            url,
        )
        return True
    except Exception as exc:
        logger.warning(
            'Failed to enqueue Cloud Task for operation %s: %s',
            operation_id,
            exc,
        )
        return False


def enqueue_orchestrator_dispatch(app, operation_id: str, operation_type: str) -> bool:
    orchestrator_base = str(app.config.get('ORCHESTRATOR_BASE_URL') or '').strip()
    if not orchestrator_base:
        return False

    url = build_dispatch_url(app, operation_id)
    request = urllib.request.Request(
        url=url,
        data=b'{}',
        headers={
            'Content-Type': 'application/json',
            'X-Internal-Job-Token': app.config.get(
                'INTERNAL_JOB_TOKEN',
                'dev-internal-job-token',
            ),
        },
        method='POST',
    )

    timeout_s = float(app.config.get('ORCHESTRATOR_REQUEST_TIMEOUT_S') or 10)
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            logger.info(
                'Dispatched operation %s (%s) to orchestrator via %s, status=%s',
                operation_id,
                operation_type,
                url,
                response.status,
            )
            return 200 <= int(response.status) < 300
    except urllib.error.URLError as exc:
        logger.warning(
            'Failed to dispatch operation %s to orchestrator %s: %s',
            operation_id,
            url,
            exc,
        )
        return False


def build_dispatch_url(app, operation_id: str) -> str:
    orchestrator_base = str(app.config.get('ORCHESTRATOR_BASE_URL') or '').strip()
    base_url = orchestrator_base or str(app.config.get('INTERNAL_BASE_URL') or '').strip()
    return f"{base_url.rstrip('/')}/internal/operations/{operation_id}/dispatch"


def spawn_operation_worker(
    app,
    operation_id: str,
    execute_callback: Callable[[str], None],
) -> None:
    thread = threading.Thread(
        target=_execute_in_app_context,
        args=(app, operation_id, execute_callback),
        daemon=True,
    )
    thread.start()


def _execute_in_app_context(
    app,
    operation_id: str,
    execute_callback: Callable[[str], None],
) -> None:
    with app.app_context():
        execute_callback(operation_id)
