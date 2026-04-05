"""Runtime guardrails for Native compute rollout."""

from __future__ import annotations

import copy
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from google.cloud import firestore

from config import Config
from services.compute_rollout_service import ComputeRolloutService
from services.history_service import HistoryService

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        normalized = str(value).replace('Z', '+00:00')
        return datetime.fromisoformat(normalized)
    except Exception:
        return None


class ComputeRolloutGuardService:
    """Persist native runtime incidents and enforce rollback safeguards."""

    CACHE_TTL_S = 15.0
    DOC_ID = 'compute_rollout_guard'
    MAX_RECENT_FAILURES = 12

    _cached_state: Dict[str, Any] | None = None
    _cached_at = 0.0

    @staticmethod
    def _get_firestore_client():
        return firestore.Client(
            project=Config.GCP_PROJECT_ID,
            database=Config.FIRESTORE_DATABASE,
        )

    @classmethod
    def _doc_ref(cls, client=None):
        client = client or cls._get_firestore_client()
        return client.collection(
            getattr(Config, 'COMPUTE_GOVERNANCE_COLLECTION', 'runtime_governance'),
        ).document(cls.DOC_ID)

    @staticmethod
    def _local_snapshot_path() -> Path:
        project_root = Path(__file__).resolve().parent.parent.parent
        return project_root / 'outputs' / 'compute_rollout_guard_local.json'

    @classmethod
    def _load_local_snapshot(cls) -> Dict[str, Any]:
        snapshot_path = cls._local_snapshot_path()
        if not snapshot_path.exists():
            return {}
        try:
            payload = json.loads(snapshot_path.read_text(encoding='utf-8'))
            if isinstance(payload, dict):
                return payload
        except Exception as exc:
            logger.warning('Failed to read local compute rollout guard snapshot: %s', exc)
        return {}

    @classmethod
    def _write_local_snapshot(cls, payload: Dict[str, Any]) -> None:
        snapshot_path = cls._local_snapshot_path()
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    @classmethod
    def _default_component_state(cls, component: str) -> Dict[str, Any]:
        label = str(
            (ComputeRolloutService.COMPONENT_METADATA.get(component) or {}).get('label')
            or component
        )
        return {
            'key': component,
            'label': label,
            'recent_failures': [],
            'recent_failure_count': 0,
            'last_failure_at': '',
            'last_failure_reason': '',
            'last_failure_context': '',
            'last_success_at': '',
            'auto_rollback_count': 0,
            'last_auto_rollback_at': '',
            'last_auto_rollback_reason': '',
            'last_auto_rollback_to': '',
        }

    @classmethod
    def _default_state(cls) -> Dict[str, Any]:
        return {
            'updated_at': '',
            'updated_by': 'system',
            'guard_enabled': bool(getattr(Config, 'COMPUTE_NATIVE_GUARD_ENABLED', True)),
            'failure_threshold': int(
                getattr(Config, 'COMPUTE_NATIVE_GUARD_FAILURE_THRESHOLD', 3) or 3,
            ),
            'window_minutes': int(
                getattr(Config, 'COMPUTE_NATIVE_GUARD_WINDOW_MINUTES', 30) or 30,
            ),
            'components': {
                component: cls._default_component_state(component)
                for component in ComputeRolloutService.COMPONENT_METADATA
            },
        }

    @classmethod
    def _trim_failures(
        cls,
        failures: List[Dict[str, Any]],
        *,
        window_minutes: int,
    ) -> List[Dict[str, Any]]:
        threshold = _utc_now() - timedelta(minutes=max(window_minutes, 1))
        trimmed: List[Dict[str, Any]] = []
        for failure in failures[-cls.MAX_RECENT_FAILURES :]:
            failure_at = _parse_iso(failure.get('at'))
            if failure_at is None or failure_at >= threshold:
                trimmed.append(
                    {
                        'at': str(failure.get('at') or ''),
                        'reason': str(failure.get('reason') or '')[:240],
                        'context': str(failure.get('context') or '')[:160],
                        'operation_id': str(failure.get('operation_id') or '')[:120],
                        'worker_key': str(failure.get('worker_key') or '')[:64],
                        'rollout_mode': str(failure.get('rollout_mode') or '')[:64],
                    }
                )
        return trimmed[-cls.MAX_RECENT_FAILURES :]

    @classmethod
    def _normalize_component_state(
        cls,
        component: str,
        payload: Dict[str, Any] | None,
        *,
        window_minutes: int,
    ) -> Dict[str, Any]:
        base = cls._default_component_state(component)
        incoming = dict(payload or {})
        recent_failures = incoming.get('recent_failures')
        recent_failures = recent_failures if isinstance(recent_failures, list) else []
        trimmed_failures = cls._trim_failures(
            [item for item in recent_failures if isinstance(item, dict)],
            window_minutes=window_minutes,
        )
        return {
            'key': component,
            'label': base['label'],
            'recent_failures': trimmed_failures,
            'recent_failure_count': len(trimmed_failures),
            'last_failure_at': str(incoming.get('last_failure_at') or ''),
            'last_failure_reason': str(incoming.get('last_failure_reason') or '')[:240],
            'last_failure_context': str(incoming.get('last_failure_context') or '')[:160],
            'last_success_at': str(incoming.get('last_success_at') or ''),
            'auto_rollback_count': int(incoming.get('auto_rollback_count') or 0),
            'last_auto_rollback_at': str(incoming.get('last_auto_rollback_at') or ''),
            'last_auto_rollback_reason': str(
                incoming.get('last_auto_rollback_reason') or '',
            )[:240],
            'last_auto_rollback_to': str(incoming.get('last_auto_rollback_to') or '')[:64],
        }

    @classmethod
    def _normalize_state(cls, payload: Dict[str, Any] | None) -> Dict[str, Any]:
        default_state = cls._default_state()
        incoming = dict(payload or {})
        window_minutes = int(
            incoming.get('window_minutes')
            or default_state.get('window_minutes')
            or 30,
        )
        components_payload = incoming.get('components')
        components_payload = (
            dict(components_payload)
            if isinstance(components_payload, dict)
            else {}
        )
        components: Dict[str, Any] = {}
        for component in ComputeRolloutService.COMPONENT_METADATA:
            components[component] = cls._normalize_component_state(
                component,
                components_payload.get(component) if isinstance(components_payload, dict) else None,
                window_minutes=window_minutes,
            )
        return {
            'updated_at': str(incoming.get('updated_at') or ''),
            'updated_by': str(incoming.get('updated_by') or 'system')[:120],
            'guard_enabled': bool(
                incoming.get('guard_enabled', default_state.get('guard_enabled', True)),
            ),
            'failure_threshold': int(
                incoming.get('failure_threshold')
                or default_state.get('failure_threshold')
                or 3,
            ),
            'window_minutes': window_minutes,
            'components': components,
        }

    @classmethod
    def _set_cache(cls, state: Dict[str, Any]) -> Dict[str, Any]:
        normalized = cls._normalize_state(state)
        cls._cached_state = normalized
        cls._cached_at = time.time()
        return copy.deepcopy(normalized)

    @classmethod
    def get_state(cls, *, force_refresh: bool = False) -> Dict[str, Any]:
        if (
            not force_refresh
            and cls._cached_state is not None
            and (time.time() - cls._cached_at) <= cls.CACHE_TTL_S
        ):
            return copy.deepcopy(cls._cached_state)

        try:
            snapshot = cls._doc_ref().get()
            raw = snapshot.to_dict() if snapshot.exists else {}
        except Exception as exc:
            logger.warning('Failed to load compute rollout guard state from Firestore: %s', exc)
            raw = cls._load_local_snapshot()

        if not raw:
            raw = cls._default_state()
        return cls._set_cache(raw)

    @classmethod
    def _persist_state(cls, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            cls._doc_ref().set(state, merge=True)
        except Exception as exc:
            logger.warning('Failed to persist compute rollout guard state: %s', exc)
            cls._write_local_snapshot(state)
        return cls._set_cache(state)

    @classmethod
    def get_component_state(
        cls,
        component: str,
        *,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        state = cls.get_state(force_refresh=force_refresh)
        component_state = state.get('components', {}).get(component)
        if isinstance(component_state, dict):
            return component_state
        return cls._default_component_state(component)

    @classmethod
    def record_native_success(
        cls,
        component: str,
        *,
        context: str = '',
    ) -> Dict[str, Any]:
        if component not in ComputeRolloutService.COMPONENT_METADATA:
            return {'component_state': {}, 'auto_rollback': None}

        state = cls.get_state(force_refresh=True)
        component_state = dict(state['components'].get(component) or {})
        component_state['last_success_at'] = _utc_now_iso()
        state['components'][component] = component_state
        state['updated_at'] = _utc_now_iso()
        state['updated_by'] = f'compute-guard-success:{context or component}'[:120]
        persisted = cls._persist_state(state)
        return {
            'component_state': dict(persisted['components'].get(component) or {}),
            'guard_enabled': bool(persisted.get('guard_enabled')),
            'failure_threshold': int(persisted.get('failure_threshold') or 3),
            'window_minutes': int(persisted.get('window_minutes') or 30),
            'auto_rollback': None,
        }

    @classmethod
    def record_native_failure(
        cls,
        component: str,
        *,
        reason: str,
        context: str = '',
        operation_id: str = '',
        worker_key: str = '',
        rollout_mode: str = '',
    ) -> Dict[str, Any]:
        if component not in ComputeRolloutService.COMPONENT_METADATA:
            return {'component_state': {}, 'auto_rollback': None}

        state = cls.get_state(force_refresh=True)
        component_state = dict(state['components'].get(component) or {})
        recent_failures = list(component_state.get('recent_failures') or [])
        recent_failures.append(
            {
                'at': _utc_now_iso(),
                'reason': str(reason or '')[:240],
                'context': str(context or '')[:160],
                'operation_id': str(operation_id or '')[:120],
                'worker_key': str(worker_key or '')[:64],
                'rollout_mode': str(rollout_mode or '')[:64],
            }
        )
        normalized_component = cls._normalize_component_state(
            component,
            {
                **component_state,
                'recent_failures': recent_failures,
                'last_failure_at': _utc_now_iso(),
                'last_failure_reason': str(reason or ''),
                'last_failure_context': str(context or ''),
            },
            window_minutes=int(state.get('window_minutes') or 30),
        )

        state['components'][component] = normalized_component
        state['updated_at'] = _utc_now_iso()
        state['updated_by'] = f'compute-guard-failure:{component}'[:120]

        auto_rollback = None
        current_policy = ComputeRolloutService.get_component_policy(
            component,
            force_refresh=True,
        )
        current_mode = str(current_policy.get('rollout_mode') or '')
        guard_enabled = bool(state.get('guard_enabled'))
        failure_threshold = int(state.get('failure_threshold') or 3)
        stable_mode = ComputeRolloutService.stable_rollout_mode(component)

        if (
            guard_enabled
            and current_mode in {'native_candidate', 'native_enforced'}
            and normalized_component['recent_failure_count'] >= max(failure_threshold, 1)
        ):
            rollback_reason = (
                f'Native fallback 在 {state.get("window_minutes")} 分钟窗口内达到 '
                f'{normalized_component["recent_failure_count"]} 次，自动回退到稳定路径'
            )
            after_policy = ComputeRolloutService.preview_component_policy(
                component,
                {
                    'rollout_mode': stable_mode,
                    'preferred_backend': 'python_pandas',
                    'canary_percent': 0,
                    'notes': rollback_reason,
                },
                updated_by='compute-guard',
            )
            ComputeRolloutService.update_policy(
                components={
                    component: {
                        'rollout_mode': stable_mode,
                        'preferred_backend': 'python_pandas',
                        'canary_percent': 0,
                        'notes': rollback_reason,
                    }
                },
                updated_by='compute-guard',
            )
            normalized_component['auto_rollback_count'] = int(
                normalized_component.get('auto_rollback_count') or 0,
            ) + 1
            normalized_component['last_auto_rollback_at'] = _utc_now_iso()
            normalized_component['last_auto_rollback_reason'] = rollback_reason
            normalized_component['last_auto_rollback_to'] = stable_mode
            state['components'][component] = normalized_component
            auto_rollback = {
                'component': component,
                'component_label': normalized_component.get('label'),
                'before_policy': current_policy,
                'after_policy': after_policy,
                'reason': rollback_reason,
                'recent_failure_count': normalized_component['recent_failure_count'],
                'window_minutes': int(state.get('window_minutes') or 30),
            }
            HistoryService.add_history(
                uid='system',
                action='compute_rollout_auto_rollback',
                status='success',
                source='compute_governance',
                resource_type='compute_rollout',
                resource_id=component,
                title=f'自动回退 Native rollout: {normalized_component.get("label")}',
                details=auto_rollback,
                severity='warning',
            )

        persisted = cls._persist_state(state)
        return {
            'component_state': dict(persisted['components'].get(component) or {}),
            'guard_enabled': bool(persisted.get('guard_enabled')),
            'failure_threshold': int(persisted.get('failure_threshold') or 3),
            'window_minutes': int(persisted.get('window_minutes') or 30),
            'auto_rollback': auto_rollback,
        }
