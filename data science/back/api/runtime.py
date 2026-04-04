"""Runtime telemetry API surfaces."""

from __future__ import annotations

from flask import Blueprint, current_app, request

from middleware.rate_limit import rate_limit
from services.compute_acceleration_service import ComputeAccelerationService
from services.firebase_service import require_auth
from utils.responses import error_response, success_response

runtime_bp = Blueprint('runtime', __name__, url_prefix='/api/runtime')
internal_runtime_bp = Blueprint('internal_runtime', __name__)


def _validate_internal_token() -> bool:
    if current_app.config.get('DEBUG') or current_app.config.get('TESTING'):
        return True
    return request.headers.get('X-Internal-Job-Token') == current_app.config.get(
        'INTERNAL_JOB_TOKEN',
    )


@runtime_bp.route('/compute-status', methods=['GET'])
@require_auth
@rate_limit(max_requests=60, window_seconds=60)
def get_compute_status():
    return success_response(ComputeAccelerationService.get_status())


@internal_runtime_bp.route('/internal/runtime/compute-status', methods=['GET'])
def internal_get_compute_status():
    if not _validate_internal_token():
        return error_response(
            'UNAUTHORIZED',
            'Internal runtime token missing',
            status_code=403,
        )
    return success_response(ComputeAccelerationService.get_status())
