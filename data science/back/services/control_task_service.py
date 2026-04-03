"""Control-task planning layer service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from google.cloud import firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from config import Config
from services.control_task_projection import serialize_control_task
from services.control_task_registry import list_default_control_tasks
from services.control_task_runtime_service import enrich_control_tasks
from services.operation_policies import default_approval_policy
from services.control_task_validation import (
    normalize_approval_policy,
    normalize_dependencies,
    normalize_owner,
    normalize_schedule,
)


class ControlTaskBackendUnavailableError(RuntimeError):
    """Raised when the configured control-task backend is unavailable."""


_UNSET = object()


class ControlTaskService:
    """Persistence and query helpers for control-plane task definitions."""

    _defaults_seeded = False

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
                parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except ValueError:
                return datetime.min.replace(tzinfo=timezone.utc)
        return datetime.min.replace(tzinfo=timezone.utc)

    @classmethod
    def ensure_default_control_tasks(cls) -> None:
        if cls._defaults_seeded:
            return

        for definition in list_default_control_tasks():
            cls.ensure_control_task(
                control_task_id=definition['control_task_id'],
                kind=definition['kind'],
                operation_type=definition.get('operation_type'),
                title=definition['title'],
                schedule=definition.get('schedule'),
                default_input=definition.get('default_input'),
                dependencies=definition.get('dependencies'),
                approval_policy=definition.get('approval_policy'),
                enabled=bool(definition.get('enabled', True)),
                owner=str(definition.get('owner') or 'system'),
            )
        cls._defaults_seeded = True

    @classmethod
    def _list_serialized_tasks(cls) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for snapshot in cls._collection().stream():
            items.append(
                serialize_control_task(
                    snapshot.to_dict() or {},
                    control_task_id=snapshot.id,
                )
            )
        items.sort(key=cls._sort_key, reverse=True)
        return items

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
                'schedule': normalize_schedule(schedule),
                'default_input': default_input or {},
                'dependencies': normalize_dependencies(dependencies),
                'approval_policy': normalize_approval_policy(
                    approval_policy or default_approval_policy(False),
                ),
                'enabled': enabled,
                'owner': normalize_owner(owner),
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
            cls.ensure_default_control_tasks()
            items = cls._list_serialized_tasks()
            if not any(item.get('id') == control_task_id for item in items):
                return None
            enriched_items = enrich_control_tasks(cls._get_firestore_client(), items)
            for item in enriched_items:
                if item.get('id') == control_task_id:
                    return item
            return None
        except Exception as exc:
            cls._wrap_backend_error(exc)

    @classmethod
    def update_control_task(
        cls,
        control_task_id: str,
        *,
        enabled: Optional[bool] = None,
        approval_policy: Optional[Dict[str, Any]] = None,
        dependencies: Any = _UNSET,
        schedule: Any = _UNSET,
        owner: Any = _UNSET,
        default_input: Any = _UNSET,
    ) -> Optional[Dict[str, Any]]:
        try:
            cls.ensure_default_control_tasks()
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
                normalized_policy = normalize_approval_policy(approval_policy)
                changes['approval_policy'] = normalized_policy
                updated['approval_policy'] = normalized_policy
            if dependencies is not _UNSET:
                normalized_dependencies = normalize_dependencies(dependencies)
                changes['dependencies'] = normalized_dependencies
                updated['dependencies'] = normalized_dependencies
            if schedule is not _UNSET:
                normalized_schedule = normalize_schedule(schedule)
                changes['schedule'] = normalized_schedule
                updated['schedule'] = normalized_schedule
            if owner is not _UNSET:
                normalized_owner = normalize_owner(owner)
                changes['owner'] = normalized_owner
                updated['owner'] = normalized_owner
            if default_input is not _UNSET:
                normalized_default_input = dict(default_input or {})
                changes['default_input'] = normalized_default_input
                updated['default_input'] = normalized_default_input

            if len(changes) == 1:
                return cls.get_control_task(control_task_id)

            document.set(changes, merge=True)
            updated = cls.get_control_task(control_task_id)
            if updated is not None:
                return updated
            fallback = snapshot.to_dict() or {}
            if enabled is not None:
                fallback['enabled'] = enabled
            if approval_policy is not None:
                fallback['approval_policy'] = normalize_approval_policy(approval_policy)
            if dependencies is not _UNSET:
                fallback['dependencies'] = normalize_dependencies(dependencies)
            if schedule is not _UNSET:
                fallback['schedule'] = normalize_schedule(schedule)
            if owner is not _UNSET:
                fallback['owner'] = normalize_owner(owner)
            if default_input is not _UNSET:
                fallback['default_input'] = dict(default_input or {})
            fallback['updated_at'] = datetime.now(timezone.utc).isoformat()
            return serialize_control_task(fallback, control_task_id=control_task_id)
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
            cls.ensure_default_control_tasks()
            items = cls._list_serialized_tasks()
            filtered: List[Dict[str, Any]] = []
            for record in items:
                if kind and record.get('kind') != kind:
                    continue
                if enabled is not None and bool(record.get('enabled')) != enabled:
                    continue
                if owner and record.get('owner') != owner:
                    continue
                filtered.append(record)
            return enrich_control_tasks(cls._get_firestore_client(), filtered[: max(1, limit)])
        except Exception as exc:
            cls._wrap_backend_error(exc)
