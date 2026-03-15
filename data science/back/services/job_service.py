"""Firestore-backed job persistence and dispatch."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flask import current_app
from google.api_core import exceptions as google_exceptions
from google.cloud import firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from config import Config
from services.history_service import HistoryService
from services.job_workflows import (
    run_analysis_workflow,
    run_deep_learning_workflow,
    run_optimization_workflow,
    run_rag_ingest_workflow,
)

logger = logging.getLogger(__name__)


class JobBackendUnavailableError(RuntimeError):
    """Raised when the configured job storage backend is unavailable."""


class JobQueryIndexRequiredError(RuntimeError):
    """Raised when Firestore query indexes are not yet available."""


class JobService:
    TERMINAL_STATUSES = {'succeeded', 'failed', 'cancelled'}

    @staticmethod
    def _wrap_backend_error(exc: Exception):
        message = str(exc)
        lowered = message.lower()
        if JobService._is_missing_index_error(exc):
            raise JobQueryIndexRequiredError('任务查询索引尚未就绪，系统已切到降级查询路径') from exc
        if (
            'datastore mode' in lowered
            and 'firestore api is not available' in lowered
        ):
            raise JobBackendUnavailableError(
                '当前部署环境未启用 Firestore Native 模式，任务中心暂不可用'
            ) from exc
        raise exc

    @staticmethod
    def _is_missing_index_error(exc: Exception) -> bool:
        if not isinstance(exc, google_exceptions.FailedPrecondition):
            return False
        message = str(exc).lower()
        return 'requires an index' in message or 'create it here' in message

    @staticmethod
    def _coerce_datetime(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        iso_value = HistoryService._as_iso(value)
        if not iso_value:
            return None
        try:
            parsed = datetime.fromisoformat(str(iso_value))
        except Exception:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    @classmethod
    def _list_jobs_without_index(
        cls,
        uid: str,
        *,
        job_type: Optional[str],
        status: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        snapshots = cls._collection().where('requested_by', '==', uid).stream()
        items: List[Dict[str, Any]] = []
        for snapshot in snapshots:
            record = snapshot.to_dict() or {}
            if job_type and record.get('type') != job_type:
                continue
            if status and record.get('status') != status:
                continue
            items.append(cls._serialize_job(record))
        items.sort(
            key=lambda record: cls._coerce_datetime(record.get('submitted_at')) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return items[:limit]

    @staticmethod
    def _get_firestore_client():
        return firestore.Client(database=Config.FIRESTORE_DATABASE)

    @classmethod
    def _collection(cls):
        return cls._get_firestore_client().collection(Config.JOBS_COLLECTION)

    @classmethod
    def create_job(cls, uid: str, job_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            doc = cls._collection().document()
            record = {
                'job_id': doc.id,
                'type': job_type,
                'status': 'queued',
                'progress': 0,
                'attempt_count': 0,
                'max_attempts': Config.TASKS_MAX_ATTEMPTS,
                'submitted_at': SERVER_TIMESTAMP,
                'started_at': None,
                'completed_at': None,
                'requested_by': uid,
                'input': payload,
                'result': None,
                'error': None,
                'status_message': 'Job queued',
                'events': [
                    {
                        'phase': 'queued',
                        'status': 'queued',
                        'message': 'Job queued',
                        'progress': 0,
                        'timestamp': datetime.utcnow().isoformat(),
                    }
                ],
            }
            doc.set(record)
            HistoryService.add_history(
                uid=uid,
                action='job_submitted',
                status='queued',
                source=job_type,
                resource_type='job',
                resource_id=doc.id,
                title=f'提交任务: {job_type}',
                details={'job_type': job_type},
            )
            return cls.get_job(uid, doc.id) or {'job_id': doc.id, **record}
        except Exception as exc:
            cls._wrap_backend_error(exc)

    @classmethod
    def get_job(cls, uid: str, job_id: str) -> Optional[Dict[str, Any]]:
        try:
            snapshot = cls._collection().document(job_id).get()
            if not snapshot.exists:
                return None
            record = snapshot.to_dict() or {}
            if record.get('requested_by') != uid:
                return None
            return cls._serialize_job(record)
        except Exception as exc:
            cls._wrap_backend_error(exc)

    @classmethod
    def get_job_for_execution(cls, job_id: str) -> Optional[Dict[str, Any]]:
        try:
            snapshot = cls._collection().document(job_id).get()
            if not snapshot.exists:
                return None
            return snapshot.to_dict() or {}
        except Exception as exc:
            cls._wrap_backend_error(exc)

    @classmethod
    def list_jobs(
        cls,
        uid: str,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        try:
            snapshots = (
                cls._collection()
                .where('requested_by', '==', uid)
                .order_by('submitted_at', direction=firestore.Query.DESCENDING)
                .limit(max(limit, 20))
                .stream()
            )
            items: List[Dict[str, Any]] = []
            for snapshot in snapshots:
                record = snapshot.to_dict() or {}
                if job_type and record.get('type') != job_type:
                    continue
                if status and record.get('status') != status:
                    continue
                items.append(cls._serialize_job(record))
                if len(items) >= limit:
                    break
            return items
        except google_exceptions.FailedPrecondition as exc:
            if cls._is_missing_index_error(exc):
                logger.warning(
                    'Firestore composite index missing for jobs query. Falling back to in-memory sort.'
                )
                return cls._list_jobs_without_index(
                    uid,
                    job_type=job_type,
                    status=status,
                    limit=limit,
                )
            cls._wrap_backend_error(exc)
        except Exception as exc:
            cls._wrap_backend_error(exc)

    @classmethod
    def retry_job(cls, uid: str, job_id: str) -> Optional[Dict[str, Any]]:
        try:
            document = cls._collection().document(job_id)
            snapshot = document.get()
            if not snapshot.exists:
                return None

            record = snapshot.to_dict() or {}
            if record.get('requested_by') != uid:
                return None
            if record.get('status') != 'failed':
                raise ValueError('只有失败任务支持重试')

            attempt_count = int(record.get('attempt_count', 0))
            max_attempts = int(record.get('max_attempts', Config.TASKS_MAX_ATTEMPTS))
            if attempt_count >= max_attempts:
                raise ValueError('任务已达到最大重试次数')

            events = cls._append_event(
                record,
                phase='queued',
                status='queued',
                message='Job requeued for retry',
                progress=0,
            )
            document.set(
                {
                    'status': 'queued',
                    'progress': 0,
                    'started_at': None,
                    'completed_at': None,
                    'result': None,
                    'error': None,
                    'status_message': 'Job requeued for retry',
                    'retryable': False,
                    'events': events,
                },
                merge=True,
            )
            HistoryService.add_history(
                uid=uid,
                action='job_retried',
                status='queued',
                source=record.get('type', 'job'),
                resource_type='job',
                resource_id=job_id,
                title=f'重试任务: {record.get("type", "job")}',
                details={'job_type': record.get('type'), 'attempt_count': attempt_count},
            )
            return cls.get_job(uid, job_id)
        except ValueError:
            raise
        except Exception as exc:
            cls._wrap_backend_error(exc)

    @classmethod
    def count_jobs(
        cls,
        uid: str,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        submitted_after: Optional[datetime] = None,
    ) -> int:
        try:
            submitted_after_dt = cls._coerce_datetime(submitted_after)
            total = 0
            for snapshot in cls._collection().where('requested_by', '==', uid).stream():
                record = snapshot.to_dict() or {}
                if job_type and record.get('type') != job_type:
                    continue
                if status and record.get('status') != status:
                    continue
                if submitted_after_dt:
                    submitted_dt = cls._coerce_datetime(record.get('submitted_at'))
                    if submitted_dt is None or submitted_dt < submitted_after_dt:
                        continue
                total += 1
            return total
        except Exception as exc:
            logger.error('Failed to count jobs: %s', exc)
            return 0

    @classmethod
    def mark_running(cls, job_id: str, *, progress: int = 10, message: str = 'Job started'):
        snapshot = cls._collection().document(job_id).get()
        current = snapshot.to_dict() or {}
        attempt_count = int(current.get('attempt_count', 0)) + 1
        events = cls._append_event(
            current,
            phase='started',
            status='running',
            message=message,
            progress=progress,
        )
        cls._collection().document(job_id).set(
            {
                'status': 'running',
                'progress': progress,
                'attempt_count': attempt_count,
                'started_at': SERVER_TIMESTAMP,
                'status_message': message,
                'events': events,
            },
            merge=True,
        )

    @classmethod
    def update_progress(cls, job_id: str, progress: int, message: str, *, phase: str = 'progress'):
        snapshot = cls._collection().document(job_id).get()
        current = snapshot.to_dict() or {}
        events = cls._append_event(
            current,
            phase=phase,
            status='running',
            message=message,
            progress=progress,
        )
        cls._collection().document(job_id).set(
            {
                'status': 'running',
                'progress': progress,
                'status_message': message,
                'events': events,
            },
            merge=True,
        )

    @classmethod
    def mark_succeeded(cls, job_id: str, result: Dict[str, Any], message: str = 'Job completed'):
        snapshot = cls._collection().document(job_id).get()
        current = snapshot.to_dict() or {}
        events = cls._append_event(
            current,
            phase='completed',
            status='succeeded',
            message=message,
            progress=100,
        )
        cls._collection().document(job_id).set(
            {
                'status': 'succeeded',
                'progress': 100,
                'completed_at': SERVER_TIMESTAMP,
                'result': result,
                'error': None,
                'status_message': message,
                'events': events,
                'retryable': False,
            },
            merge=True,
        )

    @classmethod
    def mark_failed(cls, job_id: str, *, code: str, message: str, details: Optional[Any] = None):
        snapshot = cls._collection().document(job_id).get()
        current = snapshot.to_dict() or {}
        attempt_count = int(current.get('attempt_count', 1))
        max_attempts = int(current.get('max_attempts', Config.TASKS_MAX_ATTEMPTS))
        retryable = attempt_count < max_attempts
        events = cls._append_event(
            current,
            phase='failed',
            status='failed',
            message=message,
            progress=int(current.get('progress', 0) or 0),
        )
        cls._collection().document(job_id).set(
            {
                'status': 'failed',
                'completed_at': SERVER_TIMESTAMP,
                'last_error_at': SERVER_TIMESTAMP,
                'error': {
                    'code': code,
                    'message': message,
                    'details': details,
                },
                'status_message': message,
                'retryable': retryable,
                'events': events,
            },
            merge=True,
        )

    @classmethod
    def execute_job(cls, job_id: str):
        job = cls.get_job_for_execution(job_id)
        if not job:
            logger.warning('Job %s not found for execution', job_id)
            return

        uid = job.get('requested_by')
        job_type = job.get('type')
        payload = job.get('input') or {}

        cls.mark_running(job_id, message=f'Running {job_type}')
        HistoryService.add_history(
            uid=uid,
            action='job_started',
            status='running',
            source=job_type,
            resource_type='job',
            resource_id=job_id,
            title=f'开始任务: {job_type}',
        )

        try:
            if job_type == 'optimization':
                cls.update_progress(job_id, 25, 'Predicting demand and pricing')
                result = run_optimization_workflow(uid, payload, job_id=job_id)
            elif job_type == 'analysis':
                cls.update_progress(job_id, 25, 'Preparing dataset analysis workflow', phase='dataset')
                result = run_analysis_workflow(uid, payload, job_id=job_id)
            elif job_type == 'ml_train':
                cls.update_progress(job_id, 25, 'Preparing sequence data')
                result = run_deep_learning_workflow(uid, payload, job_id=job_id)
            elif job_type == 'rag_ingest':
                cls.update_progress(job_id, 25, 'Loading and chunking documents')
                result = run_rag_ingest_workflow(uid, payload, job_id=job_id)
            else:
                raise ValueError(f'Unsupported job type: {job_type}')

            cls.mark_succeeded(job_id, result)
            HistoryService.add_history(
                uid=uid,
                action='job_completed',
                status='success',
                source=job_type,
                resource_type='job',
                resource_id=job_id,
                title=f'完成任务: {job_type}',
                details={'job_type': job_type},
            )
        except Exception as exc:
            logger.exception('Job %s failed', job_id)
            cls.mark_failed(job_id, code='JOB_FAILED', message=str(exc))
            HistoryService.add_history(
                uid=uid,
                action='job_failed',
                status='failed',
                source=job_type,
                resource_type='job',
                resource_id=job_id,
                title=f'任务失败: {job_type}',
                details={'job_type': job_type, 'message': str(exc)},
                severity='error',
            )

    @classmethod
    def dispatch_job(cls, app, job_id: str, job_type: str):
        mode = (app.config.get('TASKS_EXECUTION_MODE') or 'inline').lower()
        if mode == 'cloud_tasks' and cls._enqueue_cloud_task(app, job_id, job_type):
            return

        thread = threading.Thread(
            target=cls._execute_in_app_context,
            args=(app, job_id),
            daemon=True,
        )
        thread.start()

    @classmethod
    def _execute_in_app_context(cls, app, job_id: str):
        with app.app_context():
            cls.execute_job(job_id)

    @classmethod
    def _enqueue_cloud_task(cls, app, job_id: str, job_type: str) -> bool:
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
            url = f"{app.config.get('INTERNAL_BASE_URL').rstrip('/')}/internal/jobs/{job_type}/{job_id}"
            task = {
                'http_request': {
                    'http_method': tasks_v2.HttpMethod.POST,
                    'url': url,
                    'headers': {
                        'Content-Type': 'application/json',
                        'X-Internal-Job-Token': app.config.get('INTERNAL_JOB_TOKEN', 'dev-internal-job-token'),
                    },
                    'body': b'{}',
                }
            }
            client.create_task(parent=queue_path, task=task)
            logger.info('Enqueued Cloud Task for job %s', job_id)
            return True
        except Exception as exc:
            logger.warning('Failed to enqueue Cloud Task for job %s: %s', job_id, exc)
            return False

    @staticmethod
    def _serialize_job(record: Dict[str, Any]) -> Dict[str, Any]:
        serialized = dict(record)
        for field in ('submitted_at', 'started_at', 'completed_at'):
            serialized[field] = HistoryService._as_iso(serialized.get(field))
        raw_events = serialized.get('events')
        if isinstance(raw_events, list):
            serialized['events'] = [
                {
                    **event,
                    'timestamp': HistoryService._as_iso(event.get('timestamp')),
                }
                for event in raw_events
                if isinstance(event, dict)
            ]
        return serialized

    @staticmethod
    def _append_event(
        current: Dict[str, Any],
        *,
        phase: str,
        status: str,
        message: str,
        progress: int,
    ) -> List[Dict[str, Any]]:
        existing = current.get('events')
        events = list(existing) if isinstance(existing, list) else []
        previous = events[-1] if events else None
        if (
            isinstance(previous, dict)
            and previous.get('phase') == phase
            and previous.get('status') == status
            and previous.get('message') == message
            and int(previous.get('progress', -1)) == progress
        ):
            return events[-30:]
        events.append(
            {
                'phase': phase,
                'status': status,
                'message': message,
                'progress': progress,
                'timestamp': datetime.utcnow().isoformat(),
            }
        )
        return events[-30:]
