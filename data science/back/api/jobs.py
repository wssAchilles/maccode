"""Job orchestration API."""

from __future__ import annotations

import logging

from flask import Blueprint, current_app, request

from middleware.rate_limit import rate_limit
from services.firebase_service import require_auth
from services.job_service import JobBackendUnavailableError, JobService
from utils.exceptions import ValidationError
from utils.responses import error_response, success_response

logger = logging.getLogger(__name__)

jobs_bp = Blueprint('jobs', __name__, url_prefix='/api/jobs')
internal_jobs_bp = Blueprint('internal_jobs', __name__)

_ALLOWED_TYPES = {'analysis', 'optimization', 'ml_train', 'rag_ingest'}


def _validate_internal_token() -> bool:
    if current_app.config.get('DEBUG') or current_app.config.get('TESTING'):
        return True
    return request.headers.get('X-Internal-Job-Token') == current_app.config.get('INTERNAL_JOB_TOKEN')


@jobs_bp.route('', methods=['GET'])
@require_auth
@rate_limit(max_requests=60, window_seconds=60)
def list_jobs():
    uid = request.user.get('uid')
    job_type = request.args.get('type')
    status = request.args.get('status')
    limit = request.args.get('limit', default=20, type=int) or 20
    try:
        return success_response(
            {'jobs': JobService.list_jobs(uid, job_type=job_type, status=status, limit=min(limit, 50))}
        )
    except JobBackendUnavailableError as exc:
        logger.warning('Job backend unavailable while listing jobs for %s: %s', uid, exc)
        return success_response({'jobs': [], 'unavailable': True, 'message': str(exc)})


@jobs_bp.route('/<job_id>', methods=['GET'])
@require_auth
@rate_limit(max_requests=120, window_seconds=60)
def get_job(job_id: str):
    uid = request.user.get('uid')
    try:
        job = JobService.get_job(uid, job_id)
    except JobBackendUnavailableError as exc:
        logger.warning('Job backend unavailable while loading job %s: %s', job_id, exc)
        return error_response('JOB_BACKEND_UNAVAILABLE', str(exc), status_code=503)
    if not job:
        return error_response('JOB_NOT_FOUND', '任务不存在', status_code=404)
    return success_response(job)


@jobs_bp.route('/<job_id>/retry', methods=['POST'])
@require_auth
@rate_limit(max_requests=10, window_seconds=300)
def retry_job(job_id: str):
    uid = request.user.get('uid')
    try:
        job = JobService.retry_job(uid, job_id)
        if not job:
            return error_response('JOB_NOT_FOUND', '任务不存在', status_code=404)
        app = current_app._get_current_object()
        JobService.dispatch_job(app, job['job_id'], job['type'])
        return success_response(job, status_code=202)
    except JobBackendUnavailableError as exc:
        logger.warning('Job backend unavailable while retrying job %s: %s', job_id, exc)
        return error_response('JOB_BACKEND_UNAVAILABLE', str(exc), status_code=503)
    except ValueError as exc:
        return error_response('JOB_RETRY_INVALID', str(exc), status_code=409)
    except Exception as exc:
        logger.error('Failed to retry job %s: %s', job_id, exc, exc_info=True)
        return error_response('JOB_RETRY_ERROR', f'重试任务失败: {exc}', status_code=500)


@jobs_bp.route('/optimization', methods=['POST', 'OPTIONS'])
@require_auth
@rate_limit(max_requests=10, window_seconds=300)
def create_optimization_job():
    return _create_job('optimization')


@jobs_bp.route('/analysis', methods=['POST', 'OPTIONS'])
@require_auth
@rate_limit(max_requests=10, window_seconds=300)
def create_analysis_job():
    return _create_job('analysis')


@jobs_bp.route('/ml-train', methods=['POST', 'OPTIONS'])
@require_auth
@rate_limit(max_requests=4, window_seconds=600)
def create_ml_train_job():
    return _create_job('ml_train')


@jobs_bp.route('/rag-ingest', methods=['POST', 'OPTIONS'])
@require_auth
@rate_limit(max_requests=6, window_seconds=600)
def create_rag_ingest_job():
    return _create_job('rag_ingest')


@internal_jobs_bp.route('/internal/jobs/<job_type>/<job_id>', methods=['POST'])
def run_job(job_type: str, job_id: str):
    if job_type not in _ALLOWED_TYPES:
        return error_response('INVALID_JOB_TYPE', '不支持的任务类型', status_code=400)
    if not _validate_internal_token():
        return error_response('UNAUTHORIZED', 'Internal job token missing', status_code=403)

    JobService.execute_job(job_id)
    return success_response({'job_id': job_id, 'status': 'processed'})


def _create_job(job_type: str):
    if request.method == 'OPTIONS':
        return success_response({'status': 'ok'})

    try:
        uid = request.user.get('uid')
        payload = request.get_json() or {}
        job = JobService.create_job(uid, job_type, payload)
        app = current_app._get_current_object()
        JobService.dispatch_job(app, job['job_id'], job_type)
        return success_response(job, status_code=202)
    except JobBackendUnavailableError as exc:
        logger.warning('Job backend unavailable while creating %s job: %s', job_type, exc)
        return error_response('JOB_BACKEND_UNAVAILABLE', str(exc), status_code=503)
    except ValidationError as exc:
        return error_response('VALIDATION_ERROR', str(exc), status_code=400)
    except Exception as exc:
        logger.error('Failed to create job %s: %s', job_type, exc, exc_info=True)
        return error_response('JOB_CREATE_ERROR', f'创建任务失败: {exc}', status_code=500)
