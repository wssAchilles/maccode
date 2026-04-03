"""Unified operations and control-task persistence/orchestration service."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

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
from services.operation_dispatcher import dispatch_operation as dispatch_operation_task
from services.operation_policies import (
    approval_state_from_policy,
    default_approval_policy,
    infer_approval_policy,
)
from services.operation_projection import (
    build_event,
    coerce_datetime,
    extract_artifacts_from_result,
    finalize_step,
    now_iso,
    serialize_artifact,
    serialize_event,
    serialize_operation,
    serialize_step,
    upsert_step_summary,
)
from services.operation_tools import get_tool_contract, resolve_tool_name
from services.scheduled_operation_runner import run_fetch_data, run_train_model

logger = logging.getLogger(__name__)


class JobBackendUnavailableError(RuntimeError):
    """Raised when the configured job storage backend is unavailable."""


class JobQueryIndexRequiredError(RuntimeError):
    """Raised when Firestore query indexes are not yet available."""


class OperationCancelledError(RuntimeError):
    """Raised when a running operation has been cancelled."""


class OperationService:
    TERMINAL_STATUSES = {'succeeded', 'failed', 'cancelled'}
    EVENT_PROJECTION_LIMIT = 30
    STEP_PROJECTION_LIMIT = 20
    ARTIFACT_PROJECTION_LIMIT = 20

    @staticmethod
    def _wrap_backend_error(exc: Exception):
        message = str(exc)
        lowered = message.lower()
        if OperationService._is_missing_index_error(exc):
            raise JobQueryIndexRequiredError('任务查询索引尚未就绪，系统已切到降级查询路径') from exc
        if 'datastore mode' in lowered and 'firestore api is not available' in lowered:
            raise JobBackendUnavailableError('当前部署环境未启用 Firestore Native 模式，任务中心暂不可用') from exc
        raise exc

    @staticmethod
    def _is_missing_index_error(exc: Exception) -> bool:
        if not isinstance(exc, google_exceptions.FailedPrecondition):
            return False
        message = str(exc).lower()
        return 'requires an index' in message or 'create it here' in message

    @staticmethod
    def _coerce_datetime(value: Any) -> Optional[datetime]:
        return coerce_datetime(value)

    @staticmethod
    def _now_iso() -> str:
        return now_iso()

    @staticmethod
    def _default_approval_policy(required: bool = False, *, reason: Optional[str] = None) -> Dict[str, Any]:
        return default_approval_policy(required, reason=reason)

    @classmethod
    def _infer_approval_policy(
        cls,
        operation_type: str,
        payload: Dict[str, Any],
        explicit_policy: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return infer_approval_policy(operation_type, payload, explicit_policy)

    @classmethod
    def _approval_state_from_policy(cls, policy: Dict[str, Any]) -> Dict[str, Any]:
        return approval_state_from_policy(policy)

    @staticmethod
    def _get_firestore_client():
        return firestore.Client(database=Config.FIRESTORE_DATABASE)

    @staticmethod
    def _infer_access_scope(
        *,
        uid: str,
        control_task_id: Optional[str],
        trigger: str,
        metadata: Optional[Dict[str, Any]],
    ) -> str:
        metadata = metadata or {}
        if control_task_id or metadata.get('control_task_run') or uid == 'system':
            return 'control_plane'
        if trigger in {'scheduler', 'scheduled', 'cron', 'compat'}:
            return 'control_plane'
        return 'private'

    @staticmethod
    def _is_control_plane_operation(record: Dict[str, Any]) -> bool:
        if str(record.get('access_scope') or '').strip().lower() == 'control_plane':
            return True
        if str(record.get('control_task_id') or '').strip():
            return True
        metadata = record.get('metadata') if isinstance(record.get('metadata'), dict) else {}
        if metadata.get('control_task_run'):
            return True
        return str(record.get('requested_by') or '').strip().lower() == 'system'

    @classmethod
    def _has_operation_access(
        cls,
        uid: Optional[str],
        record: Dict[str, Any],
        *,
        write: bool = False,
    ) -> bool:
        if uid is None:
            return True
        if str(record.get('requested_by') or '') == uid:
            return True
        if cls._is_control_plane_operation(record):
            return True
        return False

    @classmethod
    def _operations_collection(cls):
        return cls._get_firestore_client().collection(Config.JOBS_COLLECTION)

    @classmethod
    def _control_tasks_collection(cls):
        return cls._get_firestore_client().collection(
            getattr(Config, 'CONTROL_TASKS_COLLECTION', 'control_tasks'),
        )

    @classmethod
    def _events_collection(cls, operation_id: str):
        return cls._operations_collection().document(operation_id).collection('events')

    @classmethod
    def _artifacts_collection(cls, operation_id: str):
        return cls._operations_collection().document(operation_id).collection('artifacts')

    @classmethod
    def ensure_control_task(
        cls,
        *,
        control_task_id: str,
        kind: str,
        title: str,
        schedule: Optional[str] = None,
        default_input: Optional[Dict[str, Any]] = None,
        dependencies: Optional[Iterable[str]] = None,
        approval_policy: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
        owner: str = 'system',
    ) -> Dict[str, Any]:
        document = cls._control_tasks_collection().document(control_task_id)
        snapshot = document.get()
        current = snapshot.to_dict() or {}
        payload = {
            'id': control_task_id,
            'kind': kind,
            'title': title,
            'schedule': schedule,
            'default_input': default_input or {},
            'dependencies': list(dependencies or ()),
            'approval_policy': approval_policy or cls._default_approval_policy(False),
            'enabled': enabled,
            'owner': owner,
            'updated_at': SERVER_TIMESTAMP,
        }
        if not snapshot.exists:
            payload['created_at'] = SERVER_TIMESTAMP
        document.set(payload, merge=True)
        return {
            **current,
            **payload,
            'updated_at': cls._now_iso(),
            'created_at': HistoryService._as_iso(current.get('created_at')) or cls._now_iso(),
        }

    @classmethod
    def create_operation(
        cls,
        uid: str,
        operation_type: str,
        payload: Dict[str, Any],
        *,
        control_task_id: Optional[str] = None,
        trigger: str = 'manual',
        approval_policy: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            document = cls._operations_collection().document()
            policy = cls._infer_approval_policy(operation_type, payload, approval_policy)
            approval_state = cls._approval_state_from_policy(policy)
            initial_status = 'awaiting_approval' if approval_state['state'] == 'pending' else 'queued'
            created_at = cls._now_iso()
            access_scope = cls._infer_access_scope(
                uid=uid,
                control_task_id=control_task_id,
                trigger=trigger,
                metadata=metadata,
            )
            record = {
                'job_id': document.id,
                'operation_id': document.id,
                'type': operation_type,
                'status': initial_status,
                'progress': 0,
                'attempt_count': 0,
                'max_attempts': Config.TASKS_MAX_ATTEMPTS,
                'submitted_at': SERVER_TIMESTAMP,
                'started_at': None,
                'completed_at': None,
                'requested_by': uid,
                'access_scope': access_scope,
                'trigger': trigger,
                'control_task_id': control_task_id,
                'input': payload,
                'output': None,
                'result': None,
                'error': None,
                'status_message': 'Waiting for approval' if initial_status == 'awaiting_approval' else 'Job queued',
                'current_step': None,
                'steps': [],
                'cancel_requested': False,
                'approval_policy': policy,
                'approval_state': approval_state,
                'metrics': {},
                'metadata': metadata or {},
                'artifacts': [],
                'events': [],
            }
            document.set(record)
            event = build_event(
                event_type='operation.created',
                phase='queued',
                status=initial_status,
                message='Operation created',
                progress=0,
                timestamp=created_at,
            )
            cls._append_event_projection(document.id, record, event)
            cls._persist_event(document.id, event)
            if approval_state['state'] == 'pending':
                approval_event = build_event(
                    event_type='approval.requested',
                    phase='approval',
                    status='awaiting_approval',
                    message=approval_state.get('reason') or 'Operation requires approval',
                    progress=0,
                )
                cls._append_event_projection(document.id, cls.get_operation_for_execution(document.id) or record, approval_event)
                cls._persist_event(document.id, approval_event)

            HistoryService.add_history(
                uid=uid,
                action='job_submitted',
                status=initial_status,
                source=operation_type,
                resource_type='job',
                resource_id=document.id,
                title=f'提交任务: {operation_type}',
                details={'job_type': operation_type, 'trigger': trigger},
            )
            return cls.get_operation(uid, document.id) or {'job_id': document.id, **record}
        except Exception as exc:
            cls._wrap_backend_error(exc)

    @classmethod
    def create_job(cls, uid: str, job_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return cls.create_operation(uid, job_type, payload)

    @classmethod
    def get_operation_for_execution(cls, operation_id: str) -> Optional[Dict[str, Any]]:
        try:
            snapshot = cls._operations_collection().document(operation_id).get()
            if not snapshot.exists:
                return None
            return snapshot.to_dict() or {}
        except Exception as exc:
            cls._wrap_backend_error(exc)

    @classmethod
    def get_job_for_execution(cls, job_id: str) -> Optional[Dict[str, Any]]:
        return cls.get_operation_for_execution(job_id)

    @classmethod
    def get_operation(
        cls,
        uid: Optional[str],
        operation_id: str,
        *,
        include_related: bool = True,
    ) -> Optional[Dict[str, Any]]:
        try:
            snapshot = cls._operations_collection().document(operation_id).get()
            if not snapshot.exists:
                return None
            record = snapshot.to_dict() or {}
            if not cls._has_operation_access(uid, record):
                return None
            serialized = serialize_operation(record)
            if include_related:
                if not serialized.get('events'):
                    serialized['events'] = cls.list_operation_events(uid, operation_id, limit=cls.EVENT_PROJECTION_LIMIT)
                serialized['artifacts'] = cls.list_operation_artifacts(uid, operation_id, limit=cls.ARTIFACT_PROJECTION_LIMIT)
            return serialized
        except Exception as exc:
            cls._wrap_backend_error(exc)

    @classmethod
    def get_job(cls, uid: str, job_id: str) -> Optional[Dict[str, Any]]:
        return cls.get_operation(uid, job_id)

    @classmethod
    def _list_operations_without_index(
        cls,
        uid: str,
        *,
        operation_type: Optional[str],
        status: Optional[str],
        limit: int,
        scope: str = 'private',
    ) -> List[Dict[str, Any]]:
        if scope == 'control_plane':
            snapshots = cls._operations_collection().stream()
        else:
            snapshots = cls._operations_collection().where('requested_by', '==', uid).stream()
        items: List[Dict[str, Any]] = []
        for snapshot in snapshots:
            record = snapshot.to_dict() or {}
            if scope == 'control_plane':
                if not cls._is_control_plane_operation(record):
                    continue
            elif record.get('requested_by') != uid:
                continue
            if operation_type and record.get('type') != operation_type:
                continue
            if status and record.get('status') != status:
                continue
            items.append(serialize_operation(record))
        items.sort(
            key=lambda record: cls._coerce_datetime(record.get('submitted_at')) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return items[:limit]

    @classmethod
    def list_operations(
        cls,
        uid: str,
        *,
        operation_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        scope: str = 'private',
    ) -> List[Dict[str, Any]]:
        try:
            base_query = cls._operations_collection().order_by(
                'submitted_at',
                direction=firestore.Query.DESCENDING,
            )
            if scope == 'control_plane':
                snapshots = base_query.limit(max(limit * 3, 20)).stream()
            else:
                snapshots = (
                    cls._operations_collection()
                    .where('requested_by', '==', uid)
                    .order_by('submitted_at', direction=firestore.Query.DESCENDING)
                    .limit(max(limit, 20))
                    .stream()
                )
            items: List[Dict[str, Any]] = []
            for snapshot in snapshots:
                record = snapshot.to_dict() or {}
                if scope == 'control_plane':
                    if not cls._is_control_plane_operation(record):
                        continue
                elif record.get('requested_by') != uid:
                    continue
                if operation_type and record.get('type') != operation_type:
                    continue
                if status and record.get('status') != status:
                    continue
                items.append(serialize_operation(record))
                if len(items) >= limit:
                    break
            return items
        except google_exceptions.FailedPrecondition as exc:
            if cls._is_missing_index_error(exc):
                logger.warning('Firestore composite index missing for operations query. Falling back to in-memory sort.')
                return cls._list_operations_without_index(
                    uid,
                    operation_type=operation_type,
                    status=status,
                    limit=limit,
                    scope=scope,
                )
            cls._wrap_backend_error(exc)
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
            for snapshot in cls._operations_collection().where('requested_by', '==', uid).stream():
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
            logger.error('Failed to count operations: %s', exc)
            return 0

    @classmethod
    def list_jobs(
        cls,
        uid: str,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        scope: str = 'private',
    ) -> List[Dict[str, Any]]:
        return cls.list_operations(
            uid,
            operation_type=job_type,
            status=status,
            limit=limit,
            scope=scope,
        )

    @classmethod
    def list_operation_events(
        cls,
        uid: Optional[str],
        operation_id: str,
        *,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        operation = cls.get_operation(uid, operation_id, include_related=False)
        if not operation:
            return []
        try:
            snapshots = list(
                cls._events_collection(operation_id)
                .order_by('timestamp', direction=firestore.Query.DESCENDING)
                .limit(max(limit, 1))
                .stream()
            )
            snapshots.reverse()
            events = [serialize_event(snapshot.to_dict() or {}) for snapshot in snapshots]
            if events:
                return events
        except Exception:
            pass
        return list(operation.get('events') or [])[-limit:]

    @classmethod
    def list_operation_artifacts(
        cls,
        uid: Optional[str],
        operation_id: str,
        *,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        operation = cls.get_operation(uid, operation_id, include_related=False)
        if not operation:
            return []
        try:
            snapshots = list(
                cls._artifacts_collection(operation_id)
                .order_by('created_at', direction=firestore.Query.DESCENDING)
                .limit(max(limit, 1))
                .stream()
            )
            snapshots.reverse()
            artifacts = [serialize_artifact(snapshot.to_dict() or {}) for snapshot in snapshots]
            if artifacts:
                return artifacts
        except Exception:
            pass
        return list(operation.get('artifacts') or [])[-limit:]

    @classmethod
    def retry_operation(cls, uid: str, operation_id: str) -> Optional[Dict[str, Any]]:
        try:
            document = cls._operations_collection().document(operation_id)
            snapshot = document.get()
            if not snapshot.exists:
                return None
            record = snapshot.to_dict() or {}
            if not cls._has_operation_access(uid, record, write=True):
                return None
            if record.get('status') not in {'failed', 'cancelled'}:
                raise ValueError('只有失败或取消的任务支持重试')

            attempt_count = int(record.get('attempt_count', 0))
            max_attempts = int(record.get('max_attempts', Config.TASKS_MAX_ATTEMPTS))
            if attempt_count >= max_attempts:
                raise ValueError('任务已达到最大重试次数')

            approval_policy = dict(record.get('approval_policy') or cls._default_approval_policy(False))
            approval_state = cls._approval_state_from_policy(approval_policy)
            status = 'awaiting_approval' if approval_state['state'] == 'pending' else 'queued'
            document.set(
                {
                    'status': status,
                    'progress': 0,
                    'started_at': None,
                    'completed_at': None,
                    'output': None,
                    'result': None,
                    'error': None,
                    'status_message': 'Operation requeued for retry',
                    'retryable': False,
                    'cancel_requested': False,
                    'current_step': None,
                    'steps': [],
                    'approval_state': approval_state,
                    'metrics': {},
                    'artifacts': [],
                },
                merge=True,
            )
            event = build_event(
                event_type='operation.retried',
                phase='queued',
                status=status,
                message='Operation requeued for retry',
                progress=0,
            )
            cls._append_event_projection(operation_id, cls.get_operation_for_execution(operation_id) or record, event)
            cls._persist_event(operation_id, event)
            HistoryService.add_history(
                uid=uid,
                action='job_retried',
                status=status,
                source=record.get('type', 'job'),
                resource_type='job',
                resource_id=operation_id,
                title=f'重试任务: {record.get("type", "job")}',
                details={'job_type': record.get('type'), 'attempt_count': attempt_count},
            )
            return cls.get_operation(uid, operation_id)
        except ValueError:
            raise
        except Exception as exc:
            cls._wrap_backend_error(exc)

    @classmethod
    def retry_job(cls, uid: str, job_id: str) -> Optional[Dict[str, Any]]:
        return cls.retry_operation(uid, job_id)

    @classmethod
    def request_cancel(cls, uid: str, operation_id: str) -> Optional[Dict[str, Any]]:
        try:
            document = cls._operations_collection().document(operation_id)
            snapshot = document.get()
            if not snapshot.exists:
                return None
            record = snapshot.to_dict() or {}
            if not cls._has_operation_access(uid, record, write=True):
                return None
            if record.get('status') in cls.TERMINAL_STATUSES:
                return cls.get_operation(uid, operation_id)

            updates: Dict[str, Any] = {
                'cancel_requested': True,
                'status_message': 'Cancellation requested',
            }
            if record.get('status') in {'queued', 'awaiting_approval', 'dispatching'}:
                updates.update(
                    {
                        'status': 'cancelled',
                        'completed_at': SERVER_TIMESTAMP,
                        'progress': int(record.get('progress', 0) or 0),
                    }
                )
            document.set(updates, merge=True)
            event_type = 'operation.cancelled' if updates.get('status') == 'cancelled' else 'operation.cancel_requested'
            event = build_event(
                event_type=event_type,
                phase='cancel',
                status=updates.get('status', record.get('status', 'running')),
                message='Operation cancelled' if event_type == 'operation.cancelled' else 'Cancellation requested',
                progress=int(record.get('progress', 0) or 0),
            )
            cls._append_event_projection(operation_id, cls.get_operation_for_execution(operation_id) or record, event)
            cls._persist_event(operation_id, event)
            return cls.get_operation(uid, operation_id)
        except Exception as exc:
            cls._wrap_backend_error(exc)

    @classmethod
    def approve_operation(
        cls,
        uid: str,
        operation_id: str,
        *,
        approved: bool,
        message: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            document = cls._operations_collection().document(operation_id)
            snapshot = document.get()
            if not snapshot.exists:
                return None
            record = snapshot.to_dict() or {}
            if not cls._has_operation_access(uid, record, write=True):
                return None

            current_state = dict(record.get('approval_state') or {})
            next_status = record.get('status', 'queued')
            if approved and current_state.get('required'):
                next_status = 'queued' if record.get('status') == 'awaiting_approval' else record.get('status', 'queued')
            elif not approved:
                next_status = 'cancelled'

            approval_state = {
                **current_state,
                'state': 'approved' if approved else 'rejected',
                'approved_by': uid,
                'approved_at': cls._now_iso(),
                'message': message,
            }
            updates: Dict[str, Any] = {
                'approval_state': approval_state,
                'status': next_status,
                'status_message': message or ('Operation approved' if approved else 'Operation rejected'),
            }
            if next_status == 'cancelled':
                updates['completed_at'] = SERVER_TIMESTAMP
                updates['cancel_requested'] = True
            document.set(updates, merge=True)

            event = build_event(
                event_type='approval.resolved',
                phase='approval',
                status=next_status,
                message=updates['status_message'],
                progress=int(record.get('progress', 0) or 0),
                extra={'approved': approved, 'approved_by': uid},
            )
            cls._append_event_projection(operation_id, cls.get_operation_for_execution(operation_id) or record, event)
            cls._persist_event(operation_id, event)
            return cls.get_operation(uid, operation_id)
        except Exception as exc:
            cls._wrap_backend_error(exc)

    @classmethod
    def claim_dispatch(cls, operation_id: str) -> Optional[Dict[str, Any]]:
        try:
            document = cls._operations_collection().document(operation_id)
            snapshot = document.get()
            if not snapshot.exists:
                return None

            record = snapshot.to_dict() or {}
            status = str(record.get('status') or '').strip()
            if status != 'queued':
                return serialize_operation(record)

            document.set(
                {
                    'status': 'dispatching',
                    'status_message': 'Dispatching to execution worker',
                },
                merge=True,
            )
            event = build_event(
                event_type='operation.dispatched',
                phase='dispatch',
                status='dispatching',
                message='Dispatching to execution worker',
                progress=int(record.get('progress', 0) or 0),
            )
            cls._append_event_projection(
                operation_id,
                cls.get_operation_for_execution(operation_id) or record,
                event,
            )
            cls._persist_event(operation_id, event)
            return cls.get_operation(None, operation_id, include_related=False)
        except Exception as exc:
            cls._wrap_backend_error(exc)

    @classmethod
    def ensure_not_cancelled(cls, operation_id: str) -> None:
        record = cls.get_operation_for_execution(operation_id)
        if record and bool(record.get('cancel_requested')):
            cls.mark_cancelled(operation_id, message='Operation cancelled by user request')
            raise OperationCancelledError('Operation cancelled')

    @classmethod
    def mark_running(cls, operation_id: str, *, progress: int = 10, message: str = 'Operation started'):
        snapshot = cls._operations_collection().document(operation_id).get()
        current = snapshot.to_dict() or {}
        attempt_count = int(current.get('attempt_count', 0)) + 1
        cls._operations_collection().document(operation_id).set(
            {
                'status': 'running',
                'progress': progress,
                'attempt_count': attempt_count,
                'started_at': SERVER_TIMESTAMP,
                'status_message': message,
            },
            merge=True,
        )
        event = build_event(
            event_type='operation.started',
            phase='started',
            status='running',
            message=message,
            progress=progress,
        )
        cls._append_event_projection(operation_id, cls.get_operation_for_execution(operation_id) or current, event)
        cls._persist_event(operation_id, event)

    @classmethod
    def update_progress(cls, operation_id: str, progress: int, message: str, *, phase: str = 'progress'):
        cls.ensure_not_cancelled(operation_id)
        snapshot = cls._operations_collection().document(operation_id).get()
        current = snapshot.to_dict() or {}
        operation_type = str(current.get('type') or '')
        tool_name = resolve_tool_name(operation_type, phase)
        tool_contract = get_tool_contract(tool_name)

        now_iso = cls._now_iso()
        steps = list(current.get('steps') or [])
        current_step = dict(current.get('current_step') or {})
        previous_phase = current_step.get('phase')
        previous_running = bool(current_step) and current_step.get('status') == 'running'

        if previous_running and previous_phase and previous_phase != phase:
            completed_step = finalize_step(current_step, status='succeeded', ended_at=now_iso)
            steps = upsert_step_summary(steps, completed_step)
            completion_event = build_event(
                event_type='step.completed',
                phase=previous_phase,
                status='succeeded',
                message=completed_step.get('message', 'Step completed'),
                progress=int(completed_step.get('progress', progress) or progress),
                step=completed_step,
            )
            cls._append_event_projection(operation_id, current, completion_event)
            cls._persist_event(operation_id, completion_event)

        if previous_phase != phase:
            next_step = {
                'phase': phase,
                'tool_name': tool_name,
                'status': 'running',
                'progress': progress,
                'message': message,
                'started_at': now_iso,
                'ended_at': None,
                'duration_ms': None,
                'execution_target': tool_contract.execution_target if tool_contract else None,
                'timeout_s': tool_contract.timeout_s if tool_contract else None,
                'retry_policy': tool_contract.retry_policy if tool_contract else None,
                'approval_policy': tool_contract.approval_policy if tool_contract else None,
                'artifact_policy': tool_contract.artifact_policy if tool_contract else None,
                'concurrency_key': tool_contract.concurrency_key if tool_contract else None,
            }
            steps = upsert_step_summary(steps, next_step)
            started_event = build_event(
                event_type='step.started',
                phase=phase,
                status='running',
                message=message,
                progress=progress,
                step=next_step,
            )
            cls._append_event_projection(operation_id, current, started_event)
            cls._persist_event(operation_id, started_event)
            current_step = next_step
        else:
            current_step = {
                **current_step,
                'status': 'running',
                'progress': progress,
                'message': message,
                'tool_name': tool_name,
                'timeout_s': current_step.get('timeout_s')
                or (tool_contract.timeout_s if tool_contract else None),
            }
            steps = upsert_step_summary(steps, current_step)

        cls._operations_collection().document(operation_id).set(
            {
                'status': 'running',
                'progress': progress,
                'status_message': message,
                'current_step': current_step,
                'steps': steps[-cls.STEP_PROJECTION_LIMIT:],
            },
            merge=True,
        )
        current = cls.get_operation_for_execution(operation_id) or current
        progress_event = build_event(
            event_type='step.progress',
            phase=phase,
            status='running',
            message=message,
            progress=progress,
            step=current_step,
        )
        cls._append_event_projection(operation_id, current, progress_event)
        cls._persist_event(operation_id, progress_event)

    @classmethod
    def mark_succeeded(cls, operation_id: str, result: Dict[str, Any], message: str = 'Operation completed'):
        snapshot = cls._operations_collection().document(operation_id).get()
        current = snapshot.to_dict() or {}
        now_iso = cls._now_iso()
        steps = list(current.get('steps') or [])
        current_step = dict(current.get('current_step') or {})
        if current_step and current_step.get('status') == 'running':
            current_step = finalize_step(current_step, status='succeeded', ended_at=now_iso, progress=100)
            steps = upsert_step_summary(steps, current_step)
            completion_event = build_event(
                event_type='step.completed',
                phase=current_step.get('phase', 'completed'),
                status='succeeded',
                message=current_step.get('message', message),
                progress=100,
                step=current_step,
            )
            cls._append_event_projection(operation_id, current, completion_event)
            cls._persist_event(operation_id, completion_event)

        artifacts = extract_artifacts_from_result(result)
        cls._operations_collection().document(operation_id).set(
            {
                'status': 'succeeded',
                'progress': 100,
                'completed_at': SERVER_TIMESTAMP,
                'output': result,
                'result': result,
                'error': None,
                'status_message': message,
                'current_step': current_step or None,
                'steps': steps[-cls.STEP_PROJECTION_LIMIT:],
                'retryable': False,
                'cancel_requested': False,
                'metrics': dict(result.get('performance') or result.get('metrics') or {}),
            },
            merge=True,
        )
        for artifact in artifacts:
            cls.add_artifact(
                operation_id,
                artifact_type=artifact['type'],
                name=artifact['name'],
                uri=artifact.get('uri'),
                metadata=artifact.get('metadata'),
            )

        event = build_event(
            event_type='operation.completed',
            phase='completed',
            status='succeeded',
            message=message,
            progress=100,
        )
        cls._append_event_projection(operation_id, cls.get_operation_for_execution(operation_id) or current, event)
        cls._persist_event(operation_id, event)

    @classmethod
    def mark_failed(cls, operation_id: str, *, code: str, message: str, details: Optional[Any] = None):
        snapshot = cls._operations_collection().document(operation_id).get()
        current = snapshot.to_dict() or {}
        if code == 'OPERATION_CANCELLED' or bool(current.get('cancel_requested')):
            cls.mark_cancelled(operation_id, message=message)
            return

        attempt_count = int(current.get('attempt_count', 1))
        max_attempts = int(current.get('max_attempts', Config.TASKS_MAX_ATTEMPTS))
        retryable = attempt_count < max_attempts
        now_iso = cls._now_iso()
        steps = list(current.get('steps') or [])
        current_step = dict(current.get('current_step') or {})
        if current_step and current_step.get('status') == 'running':
            current_step = finalize_step(current_step, status='failed', ended_at=now_iso)
            steps = upsert_step_summary(steps, current_step)
            failure_step_event = build_event(
                event_type='step.completed',
                phase=current_step.get('phase', 'failed'),
                status='failed',
                message=current_step.get('message', message),
                progress=int(current_step.get('progress', current.get('progress', 0)) or 0),
                step=current_step,
            )
            cls._append_event_projection(operation_id, current, failure_step_event)
            cls._persist_event(operation_id, failure_step_event)

        cls._operations_collection().document(operation_id).set(
            {
                'status': 'failed',
                'completed_at': SERVER_TIMESTAMP,
                'last_error_at': SERVER_TIMESTAMP,
                'error': {'code': code, 'message': message, 'details': details},
                'status_message': message,
                'retryable': retryable,
                'current_step': current_step or None,
                'steps': steps[-cls.STEP_PROJECTION_LIMIT:],
            },
            merge=True,
        )
        event = build_event(
            event_type='operation.failed',
            phase='failed',
            status='failed',
            message=message,
            progress=int(current.get('progress', 0) or 0),
        )
        cls._append_event_projection(operation_id, cls.get_operation_for_execution(operation_id) or current, event)
        cls._persist_event(operation_id, event)

    @classmethod
    def mark_cancelled(cls, operation_id: str, *, message: str = 'Operation cancelled'):
        snapshot = cls._operations_collection().document(operation_id).get()
        current = snapshot.to_dict() or {}
        now_iso = cls._now_iso()
        steps = list(current.get('steps') or [])
        current_step = dict(current.get('current_step') or {})
        if current_step and current_step.get('status') == 'running':
            current_step = finalize_step(current_step, status='cancelled', ended_at=now_iso)
            steps = upsert_step_summary(steps, current_step)
            cancelled_step_event = build_event(
                event_type='step.completed',
                phase=current_step.get('phase', 'cancelled'),
                status='cancelled',
                message=current_step.get('message', message),
                progress=int(current_step.get('progress', current.get('progress', 0)) or 0),
                step=current_step,
            )
            cls._append_event_projection(operation_id, current, cancelled_step_event)
            cls._persist_event(operation_id, cancelled_step_event)

        cls._operations_collection().document(operation_id).set(
            {
                'status': 'cancelled',
                'completed_at': SERVER_TIMESTAMP,
                'status_message': message,
                'cancel_requested': True,
                'current_step': current_step or None,
                'steps': steps[-cls.STEP_PROJECTION_LIMIT:],
            },
            merge=True,
        )
        event = build_event(
            event_type='operation.cancelled',
            phase='cancelled',
            status='cancelled',
            message=message,
            progress=int(current.get('progress', 0) or 0),
        )
        cls._append_event_projection(operation_id, cls.get_operation_for_execution(operation_id) or current, event)
        cls._persist_event(operation_id, event)

    @classmethod
    def add_artifact(
        cls,
        operation_id: str,
        *,
        artifact_type: str,
        name: str,
        uri: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = 'ready',
    ) -> Dict[str, Any]:
        artifact = {
            'type': artifact_type,
            'name': name,
            'uri': uri,
            'status': status,
            'metadata': metadata or {},
            'created_at': cls._now_iso(),
        }
        cls._persist_artifact(operation_id, artifact)
        current = cls.get_operation_for_execution(operation_id) or {}
        root_artifacts = list(current.get('artifacts') or [])
        root_artifacts.append(artifact)
        cls._operations_collection().document(operation_id).set(
            {'artifacts': root_artifacts[-cls.ARTIFACT_PROJECTION_LIMIT:]},
            merge=True,
        )
        event = build_event(
            event_type='artifact.published',
            phase='artifact',
            status='ready',
            message=f'Artifact published: {name}',
            progress=int(current.get('progress', 0) or 0),
            extra={'artifact': artifact},
        )
        cls._append_event_projection(operation_id, cls.get_operation_for_execution(operation_id) or current, event)
        cls._persist_event(operation_id, event)
        return artifact

    @classmethod
    def execute_operation(cls, operation_id: str):
        operation = cls.get_operation_for_execution(operation_id)
        if not operation:
            logger.warning('Operation %s not found for execution', operation_id)
            return

        if operation.get('status') == 'awaiting_approval':
            logger.info('Operation %s is awaiting approval; dispatch skipped', operation_id)
            return
        if bool(operation.get('cancel_requested')):
            cls.mark_cancelled(operation_id, message='Operation cancelled before execution')
            return

        uid = operation.get('requested_by')
        operation_type = operation.get('type')
        payload = operation.get('input') or {}

        cls.mark_running(operation_id, message=f'Running {operation_type}')
        HistoryService.add_history(
            uid=uid,
            action='job_started',
            status='running',
            source=operation_type,
            resource_type='job',
            resource_id=operation_id,
            title=f'开始任务: {operation_type}',
        )

        try:
            if operation_type == 'optimization':
                cls.update_progress(operation_id, 25, 'Predicting demand and pricing', phase='forecast')
                result = run_optimization_workflow(uid, payload, job_id=operation_id)
            elif operation_type == 'analysis':
                cls.update_progress(operation_id, 25, 'Preparing dataset analysis workflow', phase='dataset')
                result = run_analysis_workflow(uid, payload, job_id=operation_id)
            elif operation_type == 'ml_train':
                cls.update_progress(operation_id, 25, 'Preparing sequence data', phase='dataset')
                result = run_deep_learning_workflow(uid, payload, job_id=operation_id)
            elif operation_type == 'rag_ingest':
                cls.update_progress(operation_id, 25, 'Loading and chunking documents', phase='fetch_documents')
                result = run_rag_ingest_workflow(uid, payload, job_id=operation_id)
            elif operation_type == 'fetch_data':
                cls.update_progress(
                    operation_id,
                    35,
                    'Fetching CAISO load and OpenWeather data',
                    phase='fetch_external_data',
                )
                result = run_fetch_data(payload)
            elif operation_type == 'train_model':
                cls.update_progress(
                    operation_id,
                    35,
                    'Loading training dataset from Cloud Storage',
                    phase='prepare_dataset',
                )
                result = run_train_model(payload)
            else:
                raise ValueError(f'Unsupported operation type: {operation_type}')

            cls.mark_succeeded(operation_id, result)
            HistoryService.add_history(
                uid=uid,
                action='job_completed',
                status='success',
                source=operation_type,
                resource_type='job',
                resource_id=operation_id,
                title=f'完成任务: {operation_type}',
                details={'job_type': operation_type},
            )
        except OperationCancelledError:
            logger.info('Operation %s cancelled during execution', operation_id)
        except Exception as exc:
            logger.exception('Operation %s failed', operation_id)
            cls.mark_failed(operation_id, code='JOB_FAILED', message=str(exc))
            HistoryService.add_history(
                uid=uid,
                action='job_failed',
                status='failed',
                source=operation_type,
                resource_type='job',
                resource_id=operation_id,
                title=f'任务失败: {operation_type}',
                details={'job_type': operation_type, 'message': str(exc)},
                severity='error',
            )

    @classmethod
    def process_dispatch(cls, operation_id: str):
        operation = cls.claim_dispatch(operation_id)
        if not operation:
            logger.warning('Operation %s not found for dispatch', operation_id)
            return

        if operation.get('status') != 'dispatching':
            logger.info(
                'Operation %s dispatch ignored because status is %s',
                operation_id,
                operation.get('status'),
            )
            return

        cls.execute_operation(operation_id)

    @classmethod
    def execute_job(cls, job_id: str):
        cls.execute_operation(job_id)

    @classmethod
    def dispatch_operation(cls, app, operation_id: str, operation_type: str):
        dispatch_operation_task(
            app,
            operation_id,
            operation_type,
            execute_callback=cls.process_dispatch,
        )

    @classmethod
    def dispatch_job(cls, app, job_id: str, job_type: str):
        cls.dispatch_operation(app, job_id, job_type)

    @classmethod
    def _persist_event(cls, operation_id: str, event: Dict[str, Any]) -> None:
        payload = dict(event)
        payload['timestamp_iso'] = payload.get('timestamp') or cls._now_iso()
        payload['timestamp'] = SERVER_TIMESTAMP
        try:
            cls._events_collection(operation_id).document().set(payload)
        except Exception as exc:
            logger.warning('Failed to persist operation event for %s: %s', operation_id, exc)

    @classmethod
    def _persist_artifact(cls, operation_id: str, artifact: Dict[str, Any]) -> None:
        payload = dict(artifact)
        payload['created_at_iso'] = payload.get('created_at') or cls._now_iso()
        payload['created_at'] = SERVER_TIMESTAMP
        try:
            cls._artifacts_collection(operation_id).document().set(payload)
        except Exception as exc:
            logger.warning('Failed to persist operation artifact for %s: %s', operation_id, exc)

    @classmethod
    def _append_event_projection(cls, operation_id: str, current: Dict[str, Any], event: Dict[str, Any]) -> None:
        events = list(current.get('events') or [])
        previous = events[-1] if events else None
        if (
            isinstance(previous, dict)
            and previous.get('type') == event.get('type')
            and previous.get('phase') == event.get('phase')
            and previous.get('status') == event.get('status')
            and previous.get('message') == event.get('message')
            and int(previous.get('progress', -1)) == int(event.get('progress', -1))
        ):
            return
        events.append(event)
        cls._operations_collection().document(operation_id).set(
            {'events': events[-cls.EVENT_PROJECTION_LIMIT:]},
            merge=True,
        )
