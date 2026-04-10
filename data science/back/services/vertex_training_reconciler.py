"""Vertex callback handling and reconciliation scheduling."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from config import Config
from services.storage_service import StorageService
from services.vertex_training_service import VertexTrainingService

logger = logging.getLogger(__name__)


class VertexTrainingReconciler:
    """Accept callbacks from Vertex jobs and reconcile external state."""

    TERMINAL_STATES = {
        'JOB_STATE_SUCCEEDED',
        'JOB_STATE_FAILED',
        'JOB_STATE_CANCELLED',
        'JOB_STATE_EXPIRED',
        'JOB_STATE_PARTIALLY_SUCCEEDED',
    }

    @classmethod
    def schedule_reconcile(cls, app, operation_id: str, *, delay_s: Optional[int] = None) -> bool:
        from google.cloud import tasks_v2
        from google.protobuf import timestamp_pb2

        delay = max(int(delay_s or Config.ML_TRAIN_VERTEX_RECONCILE_DELAY_S), 5)
        try:
            client = tasks_v2.CloudTasksClient()
            queue_path = client.queue_path(
                app.config['GCP_PROJECT_ID'],
                app.config['TASKS_LOCATION'],
                app.config['TASKS_QUEUE_NAME'],
            )
            url = (
                f"{str(app.config.get('INTERNAL_BASE_URL') or '').rstrip('/')}"
                f"/internal/training/vertex/{operation_id}/reconcile"
            )
            scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
            schedule_time = timestamp_pb2.Timestamp()
            schedule_time.FromDatetime(scheduled_at)
            task = {
                'http_request': {
                    'http_method': tasks_v2.HttpMethod.POST,
                    'url': url,
                    'headers': {
                        'Content-Type': 'application/json',
                        'X-Internal-Job-Token': app.config.get('INTERNAL_JOB_TOKEN'),
                    },
                    'body': b'{}',
                },
                'schedule_time': schedule_time,
            }
            client.create_task(parent=queue_path, task=task)
            return True
        except Exception as exc:
            logger.warning('Failed to schedule Vertex reconcile for %s: %s', operation_id, exc)
            return False

    @classmethod
    def process_callback_event(
        cls,
        operation_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        from services.operation_service import OperationService

        operation = OperationService.get_operation(None, operation_id)
        if not operation:
            raise ValueError(f'Operation {operation_id} not found')
        if operation.get('status') in {'succeeded', 'failed', 'cancelled'}:
            return operation

        vertex_state = str(payload.get('vertex_state') or '').strip() or 'JOB_STATE_RUNNING'
        phase = str(payload.get('phase') or cls._phase_for_state(vertex_state)).strip()
        progress = int(payload.get('progress') or cls._progress_for_state(vertex_state))
        message = str(payload.get('message') or cls._message_for_state(vertex_state)).strip()
        metrics = dict(payload.get('metrics') or {})

        metadata = cls._update_external_job_metadata(
            operation_id,
            payload=payload,
            fallback_state=vertex_state,
        )

        if vertex_state == 'JOB_STATE_SUCCEEDED':
            result = dict(payload.get('result') or {})
            result.setdefault('training_backend', 'vertex_custom_training')
            result['external_job'] = metadata.get('external_job')
            OperationService.mark_succeeded(operation_id, result, message=message or 'Vertex training completed')
            return OperationService.get_operation(None, operation_id) or operation
        if vertex_state in {'JOB_STATE_FAILED', 'JOB_STATE_EXPIRED', 'JOB_STATE_PARTIALLY_SUCCEEDED'}:
            error = payload.get('error')
            OperationService.mark_failed(
                operation_id,
                code='VERTEX_TRAINING_FAILED',
                message=message or 'Vertex training failed',
                details=error,
            )
            return OperationService.get_operation(None, operation_id) or operation
        if vertex_state == 'JOB_STATE_CANCELLED':
            OperationService.mark_cancelled(
                operation_id,
                message=message or 'Vertex training cancelled',
            )
            return OperationService.get_operation(None, operation_id) or operation

        OperationService.update_progress(
            operation_id,
            progress,
            message,
            phase=phase,
            step_metrics=metrics,
        )
        return OperationService.get_operation(None, operation_id) or operation

    @classmethod
    def reconcile_operation(cls, app, operation_id: str) -> Dict[str, Any]:
        from services.operation_service import OperationService

        operation = OperationService.get_operation(None, operation_id)
        if not operation:
            raise ValueError(f'Operation {operation_id} not found')
        if operation.get('status') in {'succeeded', 'failed', 'cancelled'}:
            return operation
        metadata = dict(operation.get('metadata') or {})
        external_job = dict(metadata.get('external_job') or {})
        job_name = str(external_job.get('name') or '').strip()
        if not job_name:
            OperationService.mark_failed(
                operation_id,
                code='VERTEX_JOB_MISSING',
                message='Vertex external job metadata missing',
            )
            return OperationService.get_operation(None, operation_id) or operation

        snapshot = VertexTrainingService.get_job_snapshot(job_name)
        state = str(snapshot.get('state') or '')
        cls._update_external_job_metadata(
            operation_id,
            payload={'vertex_job_name': job_name, 'vertex_state': state},
            snapshot=snapshot,
            fallback_state=state,
        )

        if state == 'JOB_STATE_SUCCEEDED':
            result = cls._load_manifest_result(operation)
            if result is None:
                OperationService.mark_failed(
                    operation_id,
                    code='VERTEX_CALLBACK_MISSED',
                    message='Vertex job succeeded but manifest was not found',
                    details={'vertex_job': snapshot},
                )
            else:
                result.setdefault('training_backend', 'vertex_custom_training')
                result['external_job'] = snapshot
                OperationService.mark_succeeded(
                    operation_id,
                    result,
                    message='Vertex training completed',
                )
            return OperationService.get_operation(None, operation_id) or operation

        if state in {'JOB_STATE_FAILED', 'JOB_STATE_EXPIRED', 'JOB_STATE_PARTIALLY_SUCCEEDED'}:
            OperationService.mark_failed(
                operation_id,
                code='VERTEX_TRAINING_FAILED',
                message=cls._message_for_state(state),
                details=snapshot.get('error'),
            )
            return OperationService.get_operation(None, operation_id) or operation

        if state == 'JOB_STATE_CANCELLED':
            OperationService.mark_cancelled(
                operation_id,
                message='Vertex training cancelled',
            )
            return OperationService.get_operation(None, operation_id) or operation

        OperationService.update_progress(
            operation_id,
            cls._progress_for_state(state),
            cls._message_for_state(state),
            phase=cls._phase_for_state(state),
        )
        cls.schedule_reconcile(app, operation_id)
        return OperationService.get_operation(None, operation_id) or operation

    @classmethod
    def _update_external_job_metadata(
        cls,
        operation_id: str,
        *,
        payload: Dict[str, Any],
        snapshot: Optional[Dict[str, Any]] = None,
        fallback_state: str,
    ) -> Dict[str, Any]:
        from services.operation_service import OperationService

        current = OperationService.get_operation(None, operation_id) or {}
        metadata = dict(current.get('metadata') or {})
        external_job = dict(metadata.get('external_job') or {})
        source = snapshot or {}
        external_job.update(
            {
                'provider': 'vertex_ai',
                'name': str(
                    source.get('name')
                    or payload.get('vertex_job_name')
                    or external_job.get('name')
                    or ''
                ),
                'display_name': str(
                    source.get('display_name')
                    or external_job.get('display_name')
                    or ''
                ),
                'region': str(source.get('region') or external_job.get('region') or Config.VERTEX_REGION),
                'state': str(source.get('state') or payload.get('vertex_state') or fallback_state),
                'console_url': str(
                    source.get('console_url')
                    or external_job.get('console_url')
                    or VertexTrainingService.console_url(
                        str(source.get('name') or payload.get('vertex_job_name') or '')
                    )
                ),
                'machine_type': source.get('machine_type') or external_job.get('machine_type'),
                'accelerator_type': source.get('accelerator_type') or external_job.get('accelerator_type'),
                'accelerator_count': source.get('accelerator_count') or external_job.get('accelerator_count'),
                'started_at': source.get('started_at') or external_job.get('started_at'),
                'ended_at': source.get('ended_at') or external_job.get('ended_at'),
            }
        )
        metadata['training_backend'] = 'vertex_custom_training'
        metadata['external_job'] = external_job
        OperationService.update_operation_metadata(operation_id, metadata)
        return metadata

    @classmethod
    def _load_manifest_result(cls, operation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        requested_by = str(operation.get('requested_by') or '').strip()
        operation_id = str(operation.get('job_id') or operation.get('operation_id') or '').strip()
        if not requested_by or not operation_id:
            return None
        manifest_path = f'models/{requested_by}/runs/{operation_id}/manifest.json'
        storage = StorageService()
        if not storage.file_exists(manifest_path):
            return None
        payload = json.loads(storage.download_file(manifest_path).decode('utf-8'))
        result = payload.get('result')
        return dict(result) if isinstance(result, dict) else None

    @staticmethod
    def _phase_for_state(state: str) -> str:
        if state in {'JOB_STATE_QUEUED', 'JOB_STATE_PENDING'}:
            return 'vertex_queue'
        if state in {'JOB_STATE_RUNNING', 'JOB_STATE_PAUSED', 'JOB_STATE_UPDATING', 'JOB_STATE_CANCELLING'}:
            return 'vertex_training'
        return 'vertex_finalize'

    @staticmethod
    def _progress_for_state(state: str) -> int:
        if state == 'JOB_STATE_QUEUED':
            return 10
        if state == 'JOB_STATE_PENDING':
            return 15
        if state == 'JOB_STATE_RUNNING':
            return 20
        if state == 'JOB_STATE_CANCELLING':
            return 20
        if state in {'JOB_STATE_PAUSED', 'JOB_STATE_UPDATING'}:
            return 20
        return 100

    @staticmethod
    def _message_for_state(state: str) -> str:
        mapping = {
            'JOB_STATE_QUEUED': 'Vertex training job queued',
            'JOB_STATE_PENDING': 'Waiting for Vertex resources',
            'JOB_STATE_RUNNING': 'Vertex training container running',
            'JOB_STATE_PAUSED': 'Vertex job paused and waiting for intervention',
            'JOB_STATE_UPDATING': 'Vertex job metadata updating',
            'JOB_STATE_CANCELLING': 'Vertex job cancellation in progress',
            'JOB_STATE_SUCCEEDED': 'Vertex training completed',
            'JOB_STATE_FAILED': 'Vertex training failed',
            'JOB_STATE_CANCELLED': 'Vertex training cancelled',
            'JOB_STATE_EXPIRED': 'Vertex training expired before completion',
            'JOB_STATE_PARTIALLY_SUCCEEDED': 'Vertex training partially succeeded',
        }
        return mapping.get(state, state or 'Vertex training update')
