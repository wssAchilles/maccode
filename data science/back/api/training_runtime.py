"""Internal endpoints for Vertex training callbacks and reconciliation."""

from __future__ import annotations

import logging

from flask import Blueprint, current_app, request

from services.vertex_training_reconciler import VertexTrainingReconciler
from utils.responses import error_response, success_response

logger = logging.getLogger(__name__)

internal_training_runtime_bp = Blueprint('internal_training_runtime', __name__)


def _validate_internal_token() -> bool:
    if current_app.config.get('DEBUG') or current_app.config.get('TESTING'):
        return True
    return request.headers.get('X-Internal-Job-Token') == current_app.config.get('INTERNAL_JOB_TOKEN')


@internal_training_runtime_bp.route('/internal/training/vertex/<operation_id>/events', methods=['POST'])
def receive_vertex_training_event(operation_id: str):
    if not _validate_internal_token():
        return error_response('UNAUTHORIZED', 'Internal training token missing', status_code=403)
    try:
        payload = request.get_json() or {}
        operation = VertexTrainingReconciler.process_callback_event(operation_id, payload)
        return success_response(operation, status_code=202)
    except ValueError as exc:
        return error_response('OPERATION_NOT_FOUND', str(exc), status_code=404)
    except Exception as exc:
        logger.error('Failed to process Vertex training event for %s: %s', operation_id, exc, exc_info=True)
        return error_response('VERTEX_EVENT_ERROR', str(exc), status_code=500)


@internal_training_runtime_bp.route('/internal/training/vertex/<operation_id>/reconcile', methods=['POST'])
def reconcile_vertex_training(operation_id: str):
    if not _validate_internal_token():
        return error_response('UNAUTHORIZED', 'Internal training token missing', status_code=403)
    try:
        app = current_app._get_current_object()
        operation = VertexTrainingReconciler.reconcile_operation(app, operation_id)
        return success_response(operation, status_code=202)
    except ValueError as exc:
        return error_response('OPERATION_NOT_FOUND', str(exc), status_code=404)
    except Exception as exc:
        logger.error('Failed to reconcile Vertex training for %s: %s', operation_id, exc, exc_info=True)
        return error_response('VERTEX_RECONCILE_ERROR', str(exc), status_code=500)
