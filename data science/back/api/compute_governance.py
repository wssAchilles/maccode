"""Compute governance API surfaces."""

from __future__ import annotations

from flask import Blueprint, current_app, request

from middleware.rate_limit import rate_limit
from services.compute_governance_activity_service import ComputeGovernanceActivityService
from services.compute_governance_status_service import ComputeGovernanceStatusService
from services.compute_rollout_service import ComputeRolloutService
from services.firebase_service import require_auth
from services.operation_service import JobBackendUnavailableError, OperationService
from utils.exceptions import ValidationError
from utils.responses import error_response, success_response

compute_governance_bp = Blueprint(
    'compute_governance',
    __name__,
    url_prefix='/api/compute',
)
internal_compute_governance_bp = Blueprint(
    'internal_compute_governance',
    __name__,
)


def _validate_internal_token() -> bool:
    if current_app.config.get('DEBUG') or current_app.config.get('TESTING'):
        return True
    return request.headers.get('X-Internal-Job-Token') == current_app.config.get(
        'INTERNAL_JOB_TOKEN',
    )


@compute_governance_bp.route('/rollout', methods=['GET'])
@require_auth
@rate_limit(max_requests=60, window_seconds=60)
def get_compute_rollout():
    return success_response(ComputeGovernanceStatusService.get_policy_view())


@compute_governance_bp.route('/activity', methods=['GET'])
@require_auth
@rate_limit(max_requests=60, window_seconds=60)
def get_compute_governance_activity():
    uid = str(request.user.get('uid') or '')
    limit = min(max(request.args.get('limit', default=8, type=int) or 8, 1), 20)
    return success_response(
        {
            'entries': ComputeGovernanceActivityService.list_recent_activity(
                uid,
                limit=limit,
            )
        }
    )


@compute_governance_bp.route('/rollout', methods=['PATCH'])
@require_auth
@rate_limit(max_requests=20, window_seconds=60)
def update_compute_rollout():
    payload = request.get_json(silent=True) or {}
    components = payload.get('components')
    if components is not None and not isinstance(components, dict):
        return error_response(
            'INVALID_ARGUMENT',
            'components must be an object',
            status_code=400,
        )
    component_items = [
        (key, value)
        for key, value in dict(components or {}).items()
        if isinstance(value, dict)
    ]
    if len(component_items) != 1:
        return error_response(
            'INVALID_ARGUMENT',
            '一次只允许提交一个计算治理变更请求',
            status_code=400,
        )

    component, patch = component_items[0]
    uid = str(request.user.get('uid') or '')
    requested_by = str(request.user.get('email') or uid or 'dashboard')
    change_reason = str(payload.get('change_reason') or '').strip()

    try:
        operation = OperationService.create_operation(
            uid,
            'compute_rollout_change',
            {
                'component': component,
                'target_policy': patch,
                'change_reason': change_reason,
                'request_kind': str(payload.get('request_kind') or 'rollout_change'),
            },
            trigger='manual',
            metadata={
                'control_plane_operation': True,
                'governance_domain': 'compute_rollout',
                'requested_by_email': requested_by,
            },
        )
        if operation.get('status') == 'queued':
            app = current_app._get_current_object()
            OperationService.dispatch_operation(
                app,
                operation['job_id'],
                operation['type'],
            )
        return success_response(operation, status_code=202)
    except ValidationError as exc:
        return error_response('VALIDATION_ERROR', str(exc), status_code=400)
    except JobBackendUnavailableError as exc:
        return error_response('JOB_BACKEND_UNAVAILABLE', str(exc), status_code=503)
    except Exception as exc:
        return error_response(
            'COMPUTE_ROLLOUT_REQUEST_ERROR',
            f'提交计算治理变更失败: {exc}',
            status_code=500,
        )


@compute_governance_bp.route('/benchmark', methods=['POST'])
@require_auth
@rate_limit(max_requests=12, window_seconds=60)
def create_compute_benchmark():
    payload = request.get_json(silent=True) or {}
    component = str(payload.get('component') or '').strip()
    uid = str(request.user.get('uid') or '')
    requested_by = str(request.user.get('email') or uid or 'dashboard')
    if not component:
        return error_response(
            'INVALID_ARGUMENT',
            'component is required',
            status_code=400,
        )

    try:
        operation = OperationService.create_operation(
            uid,
            'compute_benchmark',
            {
                'component': component,
                'sample_rows': int(payload.get('sample_rows') or 5000),
                'request_kind': 'benchmark',
            },
            trigger='manual',
            metadata={
                'control_plane_operation': True,
                'governance_domain': 'compute_benchmark',
                'requested_by_email': requested_by,
            },
        )
        if operation.get('status') == 'queued':
            app = current_app._get_current_object()
            OperationService.dispatch_operation(
                app,
                operation['job_id'],
                operation['type'],
            )
        return success_response(operation, status_code=202)
    except ValidationError as exc:
        return error_response('VALIDATION_ERROR', str(exc), status_code=400)
    except JobBackendUnavailableError as exc:
        return error_response('JOB_BACKEND_UNAVAILABLE', str(exc), status_code=503)
    except Exception as exc:
        return error_response(
            'COMPUTE_BENCHMARK_REQUEST_ERROR',
            f'提交计算 benchmark 失败: {exc}',
            status_code=500,
        )


@internal_compute_governance_bp.route('/internal/compute/rollout', methods=['GET'])
def internal_get_compute_rollout():
    if not _validate_internal_token():
        return error_response(
            'UNAUTHORIZED',
            'Internal runtime token missing',
            status_code=403,
        )
    return success_response(ComputeGovernanceStatusService.get_policy_view())


@internal_compute_governance_bp.route('/internal/compute/rollout', methods=['PATCH'])
def internal_update_compute_rollout():
    if not _validate_internal_token():
        return error_response(
            'UNAUTHORIZED',
            'Internal runtime token missing',
            status_code=403,
        )
    payload = request.get_json(silent=True) or {}
    components = payload.get('components')
    if components is not None and not isinstance(components, dict):
        return error_response(
            'INVALID_ARGUMENT',
            'components must be an object',
            status_code=400,
        )
    updated = ComputeRolloutService.update_policy(
        components=components if isinstance(components, dict) else {},
        updated_by=str(payload.get('updated_by') or 'internal-runtime'),
    )
    return success_response(ComputeRolloutService.serialize_policy(updated))
