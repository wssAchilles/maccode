"""Control-task planning layer service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from google.cloud import firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from config import Config
from services.control_task_projection import serialize_control_task
from services.operation_policies import default_approval_policy


class ControlTaskBackendUnavailableError(RuntimeError):
    """Raised when the configured control-task backend is unavailable."""


class ControlTaskService:
    """Persistence and query helpers for control-plane task definitions."""

    @staticmethod
    def _get_firestore_client():
        return firestore.Client(database=Config.FIRESTORE_DATABASE)

    @classmethod
    def _collection(cls):
        return cls._get_firestore_client().collection(
            getattr(Config, 'CONTROL_TASKS_COLLECTION', 'control_tasks'),
        )

    @staticmethod
    def _is_backend_unavailable(exc: Exception) -> bool:
        message = str(exc).lower()
        return 'datastore mode' in message and 'firestore api is not available' in message

    @classmethod
    def _wrap_backend_error(cls, exc: Exception):
        if cls._is_backend_unavailable(exc):
            raise ControlTaskBackendUnavailableError(
                '当前部署环境未启用 Firestore Native 模式，规划任务中心暂不可用',
            ) from exc
        raise exc

    @staticmethod
    def _sort_key(item: Dict[str, Any]) -> datetime:
        timestamp = item.get('updated_at') or item.get('created_at')
        if isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                return datetime.min
        return datetime.min

    @classmethod
    def ensure_control_task(
        cls,
        *,
        control_task_id: str,
        kind: str,
        operation_type: Optional[str] = None,
        title: str,
        schedule: Optional[str] = None,
        default_input: Optional[Dict[str, Any]] = None,
        dependencies: Optional[Iterable[str]] = None,
        approval_policy: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
        owner: str = 'system',
    ) -> Dict[str, Any]:
        try:
            document = cls._collection().document(control_task_id)
            snapshot = document.get()
            current = snapshot.to_dict() or {}
            payload = {
                'id': control_task_id,
                'kind': kind,
                'operation_type': operation_type or current.get('operation_type'),
                'title': title,
                'schedule': schedule,
                'default_input': default_input or {},
                'dependencies': list(dependencies or ()),
                'approval_policy': approval_policy or default_approval_policy(False),
                'enabled': enabled,
                'owner': owner,
                'updated_at': SERVER_TIMESTAMP,
            }
            if not snapshot.exists:
                payload['created_at'] = SERVER_TIMESTAMP
            document.set(payload, merge=True)
            return serialize_control_task(
                {
                    **current,
                    **payload,
                },
                control_task_id=control_task_id,
            )
        except Exception as exc:
            cls._wrap_backend_error(exc)

    @classmethod
    def get_control_task(cls, control_task_id: str) -> Optional[Dict[str, Any]]:
        try:
            snapshot = cls._collection().document(control_task_id).get()
            if not snapshot.exists:
                return None
            return serialize_control_task(snapshot.to_dict() or {}, control_task_id=control_task_id)
        except Exception as exc:
            cls._wrap_backend_error(exc)

    @classmethod
    def update_control_task(
        cls,
        control_task_id: str,
        *,
        enabled: Optional[bool] = None,
        approval_policy: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            document = cls._collection().document(control_task_id)
            snapshot = document.get()
            if not snapshot.exists:
                return None

            changes: Dict[str, Any] = {'updated_at': SERVER_TIMESTAMP}
            updated = snapshot.to_dict() or {}
            if enabled is not None:
                changes['enabled'] = enabled
                updated['enabled'] = enabled
            if approval_policy is not None:
                changes['approval_policy'] = dict(approval_policy)
                updated['approval_policy'] = dict(approval_policy)

            if len(changes) == 1:
                return serialize_control_task(updated, control_task_id=control_task_id)

            document.set(changes, merge=True)
            updated = snapshot.to_dict() or {}
            if enabled is not None:
                updated['enabled'] = enabled
            if approval_policy is not None:
                updated['approval_policy'] = dict(approval_policy)
            updated['updated_at'] = datetime.now(timezone.utc).isoformat()
            return serialize_control_task(updated, control_task_id=control_task_id)
        except Exception as exc:
            cls._wrap_backend_error(exc)

    @classmethod
    def set_control_task_enabled(
        cls,
        control_task_id: str,
        *,
        enabled: bool,
    ) -> Optional[Dict[str, Any]]:
        return cls.update_control_task(control_task_id, enabled=enabled)

    @classmethod
    def set_control_task_approval_policy(
        cls,
        control_task_id: str,
        *,
        approval_policy: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        return cls.update_control_task(
            control_task_id,
            approval_policy=approval_policy,
        )

    @classmethod
    def list_control_tasks(
        cls,
        *,
        kind: Optional[str] = None,
        enabled: Optional[bool] = None,
        owner: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        try:
            snapshots = cls._collection().stream()
            items: List[Dict[str, Any]] = []
            for snapshot in snapshots:
                record = serialize_control_task(snapshot.to_dict() or {}, control_task_id=snapshot.id)
                if kind and record.get('kind') != kind:
                    continue
                if enabled is not None and bool(record.get('enabled')) != enabled:
                    continue
                if owner and record.get('owner') != owner:
                    continue
                items.append(record)
            items.sort(key=cls._sort_key, reverse=True)
            return items[: max(1, limit)]
        except Exception as exc:
            cls._wrap_backend_error(exc)
