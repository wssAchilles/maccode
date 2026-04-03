"""Dispatch boundary for operation execution.

This module owns Cloud Tasks enqueueing and local thread fallback so the
operation service can focus on state transitions and persistence.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)


def dispatch_operation(
    app,
    operation_id: str,
    operation_type: str,
    *,
    execute_callback: Callable[[str], None],
) -> None:
    mode = (app.config.get('TASKS_EXECUTION_MODE') or 'inline').lower()
    if mode == 'cloud_tasks' and enqueue_cloud_task(app, operation_id, operation_type):
        return

    thread = threading.Thread(
        target=_execute_in_app_context,
        args=(app, operation_id, execute_callback),
        daemon=True,
    )
    thread.start()


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
        logger.warning('Failed to enqueue Cloud Task for operation %s: %s', operation_id, exc)
        return False


def build_dispatch_url(app, operation_id: str) -> str:
    orchestrator_base = str(app.config.get('ORCHESTRATOR_BASE_URL') or '').strip()
    base_url = orchestrator_base or str(app.config.get('INTERNAL_BASE_URL') or '').strip()
    return f"{base_url.rstrip('/')}/internal/operations/{operation_id}/dispatch"


def _execute_in_app_context(
    app,
    operation_id: str,
    execute_callback: Callable[[str], None],
) -> None:
    with app.app_context():
        execute_callback(operation_id)
