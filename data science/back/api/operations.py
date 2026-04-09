"""Operations API and internal control-plane surfaces."""

from __future__ import annotations

import logging
from collections.abc import Iterator

import requests
from flask import Blueprint, Response, current_app, request, stream_with_context

from middleware.rate_limit import rate_limit
from services.firebase_service import require_auth
from services.operation_execution_runtime import start_internal_operation_dispatch
from services.operation_service import JobBackendUnavailableError, OperationService
from services.operation_stream import stream_operation_events
from services.operation_tool_runner import execute_operation_tool
from utils.exceptions import ValidationError
from utils.responses import error_response, success_response

logger = logging.getLogger(__name__)

operations_bp = Blueprint('operations', __name__, url_prefix='/api/operations')
internal_operations_bp = Blueprint('internal_operations', __name__)

_ALLOWED_TYPES = {
    'analysis',
    'optimization',
    'ml_train',
    'rag_ingest',
    'compute_rollout_change',
    'compute_benchmark',
}


def _validate_internal_token() -> bool:
    if current_app.config.get('DEBUG') or current_app.config.get('TESTING'):
        return True
    return request.headers.get('X-Internal-Job-Token') == current_app.config.get('INTERNAL_JOB_TOKEN')


def _orchestrator_managed_dispatch() -> bool:
    return request.headers.get('X-Orchestrator-Managed', '').strip().lower() in {
        '1',
        'true',
        'yes',
    }


def _should_run_dispatch_inline(operation: dict) -> bool:
    return str(operation.get('execution_target') or '').strip().lower() == 'heavy_worker'


def _proxy_stream_from_orchestrator(
    operation_id: str,
    *,
    poll_interval: float,
    max_duration: float,
) -> Iterator[bytes] | None:
    orchestrator_base = str(current_app.config.get('ORCHESTRATOR_BASE_URL') or '').strip()
    if not orchestrator_base:
        return None

    timeout_s = max(
        float(current_app.config.get('ORCHESTRATOR_REQUEST_TIMEOUT_S') or 10.0),
        1.0,
    )
    stream_url = f"{orchestrator_base.rstrip('/')}/internal/operations/{operation_id}/stream"

    try:
        upstream = requests.get(
            stream_url,
            headers={
                'Accept': 'text/event-stream',
                'X-Internal-Job-Token': current_app.config.get(
                    'INTERNAL_JOB_TOKEN',
                    'dev-internal-job-token',
                ),
            },
            params={
                'poll_interval': poll_interval,
                'max_duration': max_duration,
            },
            stream=True,
            timeout=(timeout_s, max(timeout_s, max_duration + 5.0)),
        )
        upstream.raise_for_status()
    except requests.RequestException as exc:
        logger.warning(
            'Failed to proxy operation %s stream from orchestrator %s: %s',
            operation_id,
            stream_url,
            exc,
        )
        try:
            upstream.close()  # type: ignore[name-defined]
        except Exception:
            pass
        return None

    def generate() -> Iterator[bytes]:
        try:
            for chunk in upstream.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    return generate()


@operations_bp.route('', methods=['GET'])
@require_auth
@rate_limit(max_requests=60, window_seconds=60)
def list_operations():
    uid = request.user.get('uid')
    operation_type = request.args.get('type')
    status = request.args.get('status')
    scope = str(request.args.get('scope') or 'private').strip().lower()
    if scope not in {'private', 'control_plane'}:
        return error_response('INVALID_SCOPE', 'scope 仅支持 private 或 control_plane', status_code=400)
    limit = request.args.get('limit', default=20, type=int) or 20
    try:
        return success_response(
            {
                'operations': OperationService.list_operations(
                    uid,
                    operation_type=operation_type,
                    status=status,
                    limit=min(limit, 50),
                    scope=scope,
                )
            }
        )
    except JobBackendUnavailableError as exc:
        logger.warning('Operation backend unavailable while listing operations for %s: %s', uid, exc)
        return success_response({'operations': [], 'unavailable': True, 'message': str(exc)})


@operations_bp.route('', methods=['POST'])
@require_auth
@rate_limit(max_requests=10, window_seconds=300)
def create_operation():
    uid = request.user.get('uid')
    payload = request.get_json() or {}
    operation_type = str(payload.get('type') or '').strip()
    if operation_type not in _ALLOWED_TYPES:
        return error_response('INVALID_OPERATION_TYPE', '不支持的任务类型', status_code=400)

    input_payload = payload.get('input')
    if not isinstance(input_payload, dict):
        reserved = {'type', 'control_task_id', 'trigger', 'approval_policy', 'metadata'}
        input_payload = {key: value for key, value in payload.items() if key not in reserved}

    try:
        operation = OperationService.create_operation(
            uid,
            operation_type,
            input_payload,
            control_task_id=payload.get('control_task_id'),
            trigger=str(payload.get('trigger') or 'manual'),
            approval_policy=payload.get('approval_policy') if isinstance(payload.get('approval_policy'), dict) else None,
            metadata=payload.get('metadata') if isinstance(payload.get('metadata'), dict) else None,
        )
        if operation.get('status') == 'queued':
            app = current_app._get_current_object()
            OperationService.dispatch_operation(app, operation['job_id'], operation_type)
        return success_response(operation, status_code=202)
    except JobBackendUnavailableError as exc:
        logger.warning('Operation backend unavailable while creating %s: %s', operation_type, exc)
        return error_response('JOB_BACKEND_UNAVAILABLE', str(exc), status_code=503)
    except ValidationError as exc:
        return error_response('VALIDATION_ERROR', str(exc), status_code=400)
    except Exception as exc:
        logger.error('Failed to create operation %s: %s', operation_type, exc, exc_info=True)
        return error_response('OPERATION_CREATE_ERROR', f'创建任务失败: {exc}', status_code=500)


@operations_bp.route('/<operation_id>', methods=['GET'])
@require_auth
@rate_limit(max_requests=120, window_seconds=60)
def get_operation(operation_id: str):
    uid = request.user.get('uid')
    try:
        operation = OperationService.get_operation(uid, operation_id)
    except JobBackendUnavailableError as exc:
        logger.warning('Operation backend unavailable while loading operation %s: %s', operation_id, exc)
        return error_response('JOB_BACKEND_UNAVAILABLE', str(exc), status_code=503)
    if not operation:
        return error_response('OPERATION_NOT_FOUND', '任务不存在', status_code=404)
    return success_response(operation)


@operations_bp.route('/<operation_id>/events', methods=['GET'])
@require_auth
@rate_limit(max_requests=120, window_seconds=60)
def get_operation_events(operation_id: str):
    uid = request.user.get('uid')
    limit = request.args.get('limit', default=50, type=int) or 50
    events = OperationService.list_operation_events(uid, operation_id, limit=min(limit, 200))
    if not events and not OperationService.get_operation(uid, operation_id, include_related=False):
        return error_response('OPERATION_NOT_FOUND', '任务不存在', status_code=404)
    return success_response({'events': events})


@operations_bp.route('/<operation_id>/stream', methods=['GET'])
@require_auth
@rate_limit(max_requests=30, window_seconds=60)
def stream_operation(operation_id: str):
    uid = request.user.get('uid')
    operation = OperationService.get_operation(uid, operation_id, include_related=False)
    if not operation:
        return error_response('OPERATION_NOT_FOUND', '任务不存在', status_code=404)

    poll_interval = request.args.get('poll_interval', default=2.0, type=float) or 2.0
    max_duration = request.args.get('max_duration', default=55.0, type=float) or 55.0
    orchestrator_stream = _proxy_stream_from_orchestrator(
        operation_id,
        poll_interval=max(0.5, min(poll_interval, 10.0)),
        max_duration=max(5.0, min(max_duration, 300.0)),
    )
    if orchestrator_stream is not None:
        return Response(
            stream_with_context(orchestrator_stream),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
            },
        )

    generator = stream_operation_events(
        operation_id=operation_id,
        fetch_operation=lambda: OperationService.get_operation(uid, operation_id),
        list_events=lambda: OperationService.list_operation_events(uid, operation_id, limit=200),
        poll_interval_s=max(0.5, min(poll_interval, 10.0)),
        max_duration_s=max(5.0, min(max_duration, 300.0)),
    )
    return Response(
        stream_with_context(generator),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


@operations_bp.route('/<operation_id>/cancel', methods=['POST'])
@require_auth
@rate_limit(max_requests=20, window_seconds=300)
def cancel_operation(operation_id: str):
    uid = request.user.get('uid')
    operation = OperationService.request_cancel(uid, operation_id)
    if not operation:
        return error_response('OPERATION_NOT_FOUND', '任务不存在', status_code=404)
    return success_response(operation, status_code=202)


@operations_bp.route('/<operation_id>/retry', methods=['POST'])
@require_auth
@rate_limit(max_requests=10, window_seconds=300)
def retry_operation(operation_id: str):
    uid = request.user.get('uid')
    try:
        operation = OperationService.retry_operation(uid, operation_id)
        if not operation:
            return error_response('OPERATION_NOT_FOUND', '任务不存在', status_code=404)
        if operation.get('status') == 'queued':
            app = current_app._get_current_object()
            OperationService.dispatch_operation(app, operation['job_id'], operation['type'])
        return success_response(operation, status_code=202)
    except JobBackendUnavailableError as exc:
        logger.warning('Operation backend unavailable while retrying operation %s: %s', operation_id, exc)
        return error_response('JOB_BACKEND_UNAVAILABLE', str(exc), status_code=503)
    except ValueError as exc:
        return error_response('OPERATION_RETRY_INVALID', str(exc), status_code=409)
    except Exception as exc:
        logger.error('Failed to retry operation %s: %s', operation_id, exc, exc_info=True)
        return error_response('OPERATION_RETRY_ERROR', f'重试任务失败: {exc}', status_code=500)


@operations_bp.route('/<operation_id>/approve', methods=['POST'])
@require_auth
@rate_limit(max_requests=20, window_seconds=300)
def approve_operation(operation_id: str):
    uid = request.user.get('uid')
    payload = request.get_json() or {}
    approved = bool(payload.get('approved', True))
    operation = OperationService.approve_operation(
        uid,
        operation_id,
        approved=approved,
        message=payload.get('message'),
    )
    if not operation:
        return error_response('OPERATION_NOT_FOUND', '任务不存在', status_code=404)
    if approved and operation.get('status') == 'queued':
        app = current_app._get_current_object()
        OperationService.dispatch_operation(app, operation['job_id'], operation['type'])
    return success_response(operation, status_code=202)


@internal_operations_bp.route('/internal/operations/<operation_id>/dispatch', methods=['POST'])
def internal_dispatch_operation(operation_id: str):
    if not _validate_internal_token():
        return error_response('UNAUTHORIZED', 'Internal operation token missing', status_code=403)
    operation = OperationService.get_operation_for_execution(operation_id)
    if not operation:
        return error_response('OPERATION_NOT_FOUND', '任务不存在', status_code=404)
    if _should_run_dispatch_inline(operation):
        OperationService.process_dispatch(operation_id)
        return success_response(
            {
                'operation_id': operation_id,
                'status': 'accepted',
                'dispatch_mode': 'inline_heavy_worker',
            },
            status_code=202,
        )
    app = current_app._get_current_object()
    dispatch_result = start_internal_operation_dispatch(
        app,
        operation_id,
        process_callback=OperationService.process_dispatch,
        fetch_callback=OperationService.get_operation_for_execution,
    )
    return success_response(dispatch_result, status_code=202)


@internal_operations_bp.route('/internal/operations/<operation_id>/cancel', methods=['POST'])
def internal_cancel_operation(operation_id: str):
    if not _validate_internal_token():
        return error_response('UNAUTHORIZED', 'Internal operation token missing', status_code=403)
    operation = OperationService.get_operation_for_execution(operation_id)
    if not operation:
        return error_response('OPERATION_NOT_FOUND', '任务不存在', status_code=404)
    requested_by = str(operation.get('requested_by') or 'system')
    updated = OperationService.request_cancel(requested_by, operation_id)
    return success_response(updated or {'operation_id': operation_id})


@internal_operations_bp.route('/internal/operations/<operation_id>/retry', methods=['POST'])
def internal_retry_operation(operation_id: str):
    if not _validate_internal_token():
        return error_response('UNAUTHORIZED', 'Internal operation token missing', status_code=403)
    operation = OperationService.get_operation_for_execution(operation_id)
    if not operation:
        return error_response('OPERATION_NOT_FOUND', '任务不存在', status_code=404)
    requested_by = str(operation.get('requested_by') or 'system')
    updated = OperationService.retry_operation(requested_by, operation_id)
    if (
        updated
        and updated.get('status') == 'queued'
        and not _orchestrator_managed_dispatch()
    ):
        app = current_app._get_current_object()
        OperationService.dispatch_operation(app, updated['job_id'], updated['type'])
    return success_response(updated or {'operation_id': operation_id})


@internal_operations_bp.route('/internal/operations/<operation_id>/approve', methods=['POST'])
def internal_approve_operation(operation_id: str):
    if not _validate_internal_token():
        return error_response('UNAUTHORIZED', 'Internal operation token missing', status_code=403)
    operation = OperationService.get_operation_for_execution(operation_id)
    if not operation:
        return error_response('OPERATION_NOT_FOUND', '任务不存在', status_code=404)
    payload = request.get_json() or {}
    requested_by = str(operation.get('requested_by') or 'system')
    updated = OperationService.approve_operation(
        requested_by,
        operation_id,
        approved=bool(payload.get('approved', True)),
        message=payload.get('message'),
    )
    if (
        bool(payload.get('approved', True))
        and updated
        and updated.get('status') == 'queued'
        and not _orchestrator_managed_dispatch()
    ):
        app = current_app._get_current_object()
        OperationService.dispatch_operation(app, updated['job_id'], updated['type'])
    return success_response(updated or {'operation_id': operation_id})


@internal_operations_bp.route('/internal/operations/<operation_id>', methods=['GET'])
def internal_get_operation(operation_id: str):
    if not _validate_internal_token():
        return error_response('UNAUTHORIZED', 'Internal operation token missing', status_code=403)
    operation = OperationService.get_operation(None, operation_id)
    if not operation:
        return error_response('OPERATION_NOT_FOUND', '任务不存在', status_code=404)
    return success_response(operation)


@internal_operations_bp.route('/internal/operations/<operation_id>/events', methods=['GET'])
def internal_get_operation_events(operation_id: str):
    if not _validate_internal_token():
        return error_response('UNAUTHORIZED', 'Internal operation token missing', status_code=403)
    limit = request.args.get('limit', default=100, type=int) or 100
    events = OperationService.list_operation_events(None, operation_id, limit=min(limit, 500))
    return success_response({'events': events})


@internal_operations_bp.route('/internal/operations/<operation_id>/stream', methods=['GET'])
def internal_stream_operation(operation_id: str):
    if not _validate_internal_token():
        return error_response('UNAUTHORIZED', 'Internal operation token missing', status_code=403)
    operation = OperationService.get_operation(None, operation_id, include_related=False)
    if not operation:
        return error_response('OPERATION_NOT_FOUND', '任务不存在', status_code=404)

    poll_interval = request.args.get('poll_interval', default=2.0, type=float) or 2.0
    max_duration = request.args.get('max_duration', default=55.0, type=float) or 55.0
    generator = stream_operation_events(
        operation_id=operation_id,
        fetch_operation=lambda: OperationService.get_operation(None, operation_id),
        list_events=lambda: OperationService.list_operation_events(None, operation_id, limit=500),
        poll_interval_s=max(0.5, min(poll_interval, 10.0)),
        max_duration_s=max(5.0, min(max_duration, 300.0)),
    )
    return Response(
        stream_with_context(generator),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


@internal_operations_bp.route('/internal/tools/<tool_name>/execute', methods=['POST'])
def internal_execute_tool(tool_name: str):
    if not _validate_internal_token():
        return error_response('UNAUTHORIZED', 'Internal tool token missing', status_code=403)

    try:
        payload = request.get_json() or {}
        response = execute_operation_tool(tool_name, payload)
        return success_response(response)
    except ValidationError as exc:
        return error_response('TOOL_EXECUTION_INVALID', str(exc), status_code=400)
    except Exception as exc:
        logger.error('Internal tool execution failed for %s: %s', tool_name, exc, exc_info=True)
        return error_response('TOOL_EXECUTION_ERROR', str(exc), status_code=500)
