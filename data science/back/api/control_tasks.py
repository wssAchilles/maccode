"""Control-task planning API."""

from __future__ import annotations

import logging

from flask import Blueprint, current_app, request

from services.control_task_runner import (
    ControlTaskConfigurationError,
    ControlTaskDependencyBlockedError,
    ControlTaskDisabledError,
    ControlTaskNotFoundError,
    run_control_task as trigger_control_task_run,
)
from middleware.rate_limit import rate_limit
from services.control_task_service import (
    ControlTaskBackendUnavailableError,
    ControlTaskService,
)
from services.control_task_validation import ControlTaskValidationError
from services.firebase_service import require_auth
from services.operation_service import OperationService
from utils.responses import error_response, success_response

logger = logging.getLogger(__name__)

control_tasks_bp = Blueprint('control_tasks', __name__, url_prefix='/api/control-tasks')
internal_control_tasks_bp = Blueprint('internal_control_tasks', __name__)
_UNSET = object()


def _parse_bool_query(value: str | None):
    if value is None or value == '':
        return None
    normalized = value.strip().lower()
    if normalized in {'1', 'true', 'yes'}:
        return True
    if normalized in {'0', 'false', 'no'}:
        return False
    return None


def _validate_internal_token() -> bool:
    if current_app.config.get('DEBUG') or current_app.config.get('TESTING'):
        return True
    return request.headers.get('X-Internal-Job-Token') == current_app.config.get('INTERNAL_JOB_TOKEN')


def _parse_control_task_update_payload(payload: dict):
    updates = {
        'enabled': None,
        'approval_policy': None,
        'dependencies': _UNSET,
        'schedule': _UNSET,
        'owner': _UNSET,
        'default_input': _UNSET,
    }

    if 'enabled' in payload:
        updates['enabled'] = bool(payload.get('enabled'))

    if 'approval_policy' in payload:
        if not isinstance(payload.get('approval_policy'), dict):
            return None, error_response(
                'CONTROL_TASK_UPDATE_INVALID',
                'approval_policy 必须是对象',
                status_code=400,
            )
        updates['approval_policy'] = dict(payload.get('approval_policy') or {})

    if 'dependencies' in payload:
        raw_dependencies = payload.get('dependencies')
        if raw_dependencies is not None and not isinstance(raw_dependencies, list):
            return None, error_response(
                'CONTROL_TASK_UPDATE_INVALID',
                'dependencies 必须是字符串数组或 null',
                status_code=400,
            )
        updates['dependencies'] = list(raw_dependencies or [])

    if 'schedule' in payload:
        raw_schedule = payload.get('schedule')
        if raw_schedule is not None and not isinstance(raw_schedule, str):
            return None, error_response(
                'CONTROL_TASK_UPDATE_INVALID',
                'schedule 必须是字符串或 null',
                status_code=400,
            )
        updates['schedule'] = raw_schedule

    if 'owner' in payload:
        raw_owner = payload.get('owner')
        if raw_owner is not None and not isinstance(raw_owner, str):
            return None, error_response(
                'CONTROL_TASK_UPDATE_INVALID',
                'owner 必须是字符串或 null',
                status_code=400,
            )
        updates['owner'] = raw_owner

    if 'default_input' in payload:
        raw_default_input = payload.get('default_input')
        if raw_default_input is not None and not isinstance(raw_default_input, dict):
            return None, error_response(
                'CONTROL_TASK_UPDATE_INVALID',
                'default_input 必须是对象或 null',
                status_code=400,
            )
        updates['default_input'] = dict(raw_default_input or {})

    has_changes = (
        updates['enabled'] is not None or
        updates['approval_policy'] is not None or
        updates['dependencies'] is not _UNSET or
        updates['schedule'] is not _UNSET or
        updates['owner'] is not _UNSET or
        updates['default_input'] is not _UNSET
    )
    if not has_changes:
        return None, error_response(
            'CONTROL_TASK_UPDATE_INVALID',
            '当前支持更新 enabled、approval_policy、dependencies、schedule、owner、default_input 字段',
            status_code=400,
        )

    return updates, None


@control_tasks_bp.route('', methods=['GET'])
@require_auth
@rate_limit(max_requests=60, window_seconds=60)
def list_control_tasks():
    kind = request.args.get('kind')
    owner = request.args.get('owner')
    enabled = _parse_bool_query(request.args.get('enabled'))
    limit = request.args.get('limit', default=20, type=int) or 20

    try:
        return success_response(
            {
                'control_tasks': ControlTaskService.list_control_tasks(
                    kind=kind,
                    enabled=enabled,
                    owner=owner,
                    limit=min(limit, 100),
                )
            }
        )
    except ControlTaskBackendUnavailableError as exc:
        logger.warning('Control task backend unavailable while listing tasks: %s', exc)
        return success_response({'control_tasks': [], 'unavailable': True, 'message': str(exc)})


@control_tasks_bp.route('/<control_task_id>', methods=['GET'])
@require_auth
@rate_limit(max_requests=120, window_seconds=60)
def get_control_task(control_task_id: str):
    try:
        task = ControlTaskService.get_control_task(control_task_id)
    except ControlTaskBackendUnavailableError as exc:
        logger.warning('Control task backend unavailable while loading %s: %s', control_task_id, exc)
        return error_response('CONTROL_TASK_BACKEND_UNAVAILABLE', str(exc), status_code=503)

    if not task:
        return error_response('CONTROL_TASK_NOT_FOUND', '规划任务不存在', status_code=404)
    return success_response(task)


@control_tasks_bp.route('/<control_task_id>', methods=['PATCH'])
@require_auth
@rate_limit(max_requests=20, window_seconds=300)
def update_control_task(control_task_id: str):
    payload = request.get_json() or {}
    updates, error = _parse_control_task_update_payload(payload)
    if error is not None:
        return error
    try:
        task = ControlTaskService.update_control_task(
            control_task_id,
            enabled=updates['enabled'],
            approval_policy=updates['approval_policy'],
            dependencies=updates['dependencies'],
            schedule=updates['schedule'],
            owner=updates['owner'],
            default_input=updates['default_input'],
        )
    except ControlTaskBackendUnavailableError as exc:
        logger.warning('Control task backend unavailable while updating %s: %s', control_task_id, exc)
        return error_response('CONTROL_TASK_BACKEND_UNAVAILABLE', str(exc), status_code=503)
    except ControlTaskValidationError as exc:
        return error_response('CONTROL_TASK_UPDATE_INVALID', str(exc), status_code=400)

    if not task:
        return error_response('CONTROL_TASK_NOT_FOUND', '规划任务不存在', status_code=404)
    return success_response(task, status_code=202)


@control_tasks_bp.route('/<control_task_id>/run', methods=['POST'])
@require_auth
@rate_limit(max_requests=20, window_seconds=300)
def run_control_task(control_task_id: str):
    uid = request.user.get('uid')
    payload = request.get_json() or {}
    input_payload = payload.get('input') if isinstance(payload.get('input'), dict) else {}
    trigger = str(payload.get('trigger') or 'manual')

    try:
        operation = trigger_control_task_run(
            uid=uid,
            control_task_id=control_task_id,
            input_overrides=input_payload,
            trigger=trigger,
        )
        if operation.get('status') == 'queued':
            app = current_app._get_current_object()
            OperationService.dispatch_operation(app, operation['job_id'], operation['type'])
        return success_response(operation, status_code=202)
    except ControlTaskBackendUnavailableError as exc:
        logger.warning('Control task backend unavailable while running %s: %s', control_task_id, exc)
        return error_response('CONTROL_TASK_BACKEND_UNAVAILABLE', str(exc), status_code=503)
    except ControlTaskNotFoundError as exc:
        return error_response('CONTROL_TASK_NOT_FOUND', str(exc), status_code=404)
    except ControlTaskDisabledError as exc:
        return error_response('CONTROL_TASK_DISABLED', str(exc), status_code=409)
    except ControlTaskDependencyBlockedError as exc:
        return error_response('CONTROL_TASK_DEPENDENCY_BLOCKED', str(exc), status_code=409)
    except ControlTaskConfigurationError as exc:
        return error_response('CONTROL_TASK_INVALID', str(exc), status_code=400)
    except Exception as exc:
        logger.error('Failed to run control task %s: %s', control_task_id, exc, exc_info=True)
        return error_response('CONTROL_TASK_RUN_ERROR', f'触发规划任务失败: {exc}', status_code=500)


@internal_control_tasks_bp.route('/internal/control-tasks/<control_task_id>/run', methods=['POST'])
def internal_run_control_task(control_task_id: str):
    if not _validate_internal_token():
        return error_response('UNAUTHORIZED', 'Internal operation token missing', status_code=403)

    payload = request.get_json() or {}
    input_payload = payload.get('input') if isinstance(payload.get('input'), dict) else {}
    trigger = str(payload.get('trigger') or 'manual')
    requested_by = str(payload.get('requested_by') or 'system')

    try:
        operation = trigger_control_task_run(
            uid=requested_by,
            control_task_id=control_task_id,
            input_overrides=input_payload,
            trigger=trigger,
        )
        if operation.get('status') == 'queued':
            app = current_app._get_current_object()
            OperationService.dispatch_operation(app, operation['job_id'], operation['type'])
        return success_response(operation, status_code=202)
    except ControlTaskBackendUnavailableError as exc:
        logger.warning('Control task backend unavailable while internally running %s: %s', control_task_id, exc)
        return error_response('CONTROL_TASK_BACKEND_UNAVAILABLE', str(exc), status_code=503)
    except ControlTaskNotFoundError as exc:
        return error_response('CONTROL_TASK_NOT_FOUND', str(exc), status_code=404)
    except ControlTaskDisabledError as exc:
        return error_response('CONTROL_TASK_DISABLED', str(exc), status_code=409)
    except ControlTaskDependencyBlockedError as exc:
        return error_response('CONTROL_TASK_DEPENDENCY_BLOCKED', str(exc), status_code=409)
    except ControlTaskConfigurationError as exc:
        return error_response('CONTROL_TASK_INVALID', str(exc), status_code=400)
    except Exception as exc:
        logger.error('Failed to internally run control task %s: %s', control_task_id, exc, exc_info=True)
        return error_response('CONTROL_TASK_RUN_ERROR', f'触发规划任务失败: {exc}', status_code=500)


@internal_control_tasks_bp.route('/internal/control-tasks', methods=['GET'])
def internal_list_control_tasks():
    if not _validate_internal_token():
        return error_response('UNAUTHORIZED', 'Internal operation token missing', status_code=403)

    kind = request.args.get('kind')
    owner = request.args.get('owner')
    enabled = _parse_bool_query(request.args.get('enabled'))
    limit = request.args.get('limit', default=20, type=int) or 20
    try:
        return success_response(
            {
                'control_tasks': ControlTaskService.list_control_tasks(
                    kind=kind,
                    enabled=enabled,
                    owner=owner,
                    limit=min(limit, 100),
                )
            }
        )
    except ControlTaskBackendUnavailableError as exc:
        return error_response('CONTROL_TASK_BACKEND_UNAVAILABLE', str(exc), status_code=503)


@internal_control_tasks_bp.route('/internal/control-tasks/<control_task_id>', methods=['GET'])
def internal_get_control_task(control_task_id: str):
    if not _validate_internal_token():
        return error_response('UNAUTHORIZED', 'Internal operation token missing', status_code=403)
    try:
        task = ControlTaskService.get_control_task(control_task_id)
    except ControlTaskBackendUnavailableError as exc:
        return error_response('CONTROL_TASK_BACKEND_UNAVAILABLE', str(exc), status_code=503)
    except ControlTaskValidationError as exc:
        return error_response('CONTROL_TASK_UPDATE_INVALID', str(exc), status_code=400)

    if not task:
        return error_response('CONTROL_TASK_NOT_FOUND', '规划任务不存在', status_code=404)
    return success_response(task)


@internal_control_tasks_bp.route('/internal/control-tasks/<control_task_id>', methods=['PATCH'])
def internal_update_control_task(control_task_id: str):
    if not _validate_internal_token():
        return error_response('UNAUTHORIZED', 'Internal operation token missing', status_code=403)

    payload = request.get_json() or {}
    updates, error = _parse_control_task_update_payload(payload)
    if error is not None:
        return error

    try:
        task = ControlTaskService.update_control_task(
            control_task_id,
            enabled=updates['enabled'],
            approval_policy=updates['approval_policy'],
            dependencies=updates['dependencies'],
            schedule=updates['schedule'],
            owner=updates['owner'],
            default_input=updates['default_input'],
        )
    except ControlTaskBackendUnavailableError as exc:
        return error_response('CONTROL_TASK_BACKEND_UNAVAILABLE', str(exc), status_code=503)

    if not task:
        return error_response('CONTROL_TASK_NOT_FOUND', '规划任务不存在', status_code=404)
    return success_response(task, status_code=202)
