"""Compute governance API surfaces."""

from __future__ import annotations

from flask import Blueprint, current_app, request

from middleware.rate_limit import rate_limit
from services.compute_rollout_service import ComputeRolloutService
from services.firebase_service import require_auth
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
    return success_response(ComputeRolloutService.serialize_policy())


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
    updated = ComputeRolloutService.update_policy(
        components=components if isinstance(components, dict) else {},
        updated_by=str(request.user.get('email') or request.user.get('uid') or 'dashboard'),
    )
    return success_response(ComputeRolloutService.serialize_policy(updated))


@internal_compute_governance_bp.route('/internal/compute/rollout', methods=['GET'])
def internal_get_compute_rollout():
    if not _validate_internal_token():
        return error_response(
            'UNAUTHORIZED',
            'Internal runtime token missing',
            status_code=403,
        )
    return success_response(ComputeRolloutService.serialize_policy())
