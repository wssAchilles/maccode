"""Runtime telemetry API surfaces."""

from __future__ import annotations

from flask import Blueprint, current_app, request

from middleware.rate_limit import rate_limit
from services.compute_acceleration_service import ComputeAccelerationService
from services.compute_worker_capability_service import ComputeWorkerCapabilityService
from services.firebase_service import require_auth
from services.runtime_cache_service import RuntimeCacheService
from services.runtime_snapshot_service import RuntimeSnapshotService
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


@runtime_bp.route('/snapshot', methods=['GET'])
@require_auth
@rate_limit(max_requests=60, window_seconds=60)
def get_runtime_snapshot():
    uid = str(request.user.get('uid') or '')
    force_refresh = str(request.args.get('fresh') or '').lower() in {
        '1',
        'true',
        'yes',
    }
    if force_refresh:
        snapshot = RuntimeSnapshotService.build_shell_snapshot(uid)
    else:
        snapshot = RuntimeCacheService.get_or_set(
            f'runtime:snapshot:{uid}',
            lambda: RuntimeSnapshotService.build_shell_snapshot(uid),
            ttl_s=20,
        )
    return success_response(snapshot)


@runtime_bp.route('/worker-capability', methods=['GET'])
@require_auth
@rate_limit(max_requests=60, window_seconds=60)
def get_worker_capability():
    return success_response(ComputeWorkerCapabilityService.get_local_capability())


@internal_runtime_bp.route('/internal/runtime/compute-status', methods=['GET'])
def internal_get_compute_status():
    if not _validate_internal_token():
        return error_response(
            'UNAUTHORIZED',
            'Internal runtime token missing',
            status_code=403,
        )
    return success_response(ComputeAccelerationService.get_status())


@internal_runtime_bp.route('/internal/runtime/snapshot', methods=['GET'])
def internal_get_runtime_snapshot():
    if not _validate_internal_token():
        return error_response(
            'UNAUTHORIZED',
            'Internal runtime token missing',
            status_code=403,
        )
    uid = str(request.args.get('uid') or 'system')
    force_refresh = str(request.args.get('fresh') or '').lower() in {
        '1',
        'true',
        'yes',
    }
    if force_refresh:
        snapshot = RuntimeSnapshotService.build_shell_snapshot(uid)
    else:
        snapshot = RuntimeCacheService.get_or_set(
            f'runtime:snapshot:{uid}',
            lambda: RuntimeSnapshotService.build_shell_snapshot(uid),
            ttl_s=20,
        )
    return success_response(snapshot)


@internal_runtime_bp.route('/internal/runtime/worker-capability', methods=['GET'])
def internal_get_worker_capability():
    if not _validate_internal_token():
        return error_response(
            'UNAUTHORIZED',
            'Internal runtime token missing',
            status_code=403,
        )
    worker_key = str(request.args.get('worker_key') or 'light_worker')
    return success_response(
        ComputeWorkerCapabilityService.get_local_capability(worker_key=worker_key),
    )
