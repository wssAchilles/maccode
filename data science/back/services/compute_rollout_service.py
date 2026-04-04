"""Governance policy for compute backend rollout.

Keeps rollout policy persistence separate from profiling and kernel execution so
the hot path can read a compact, validated backend policy.
"""

from __future__ import annotations

import copy
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from google.cloud import firestore

from config import Config

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ComputeRolloutService:
    """Persist and normalize compute rollout policy."""

    CACHE_TTL_S = 15.0

    COMPONENT_METADATA = {
        'feature_engineering': {
            'label': '高级特征工程',
            'allowed_backends': ('python_pandas', 'native_cpp'),
            'allowed_modes': (
                'python_stable',
                'native_candidate',
                'native_enforced',
            ),
            'default_mode': 'python_stable',
            'default_backend': 'python_pandas',
            'default_canary_percent': 0,
            'default_require_benchmark': True,
        },
        'scenario_simulation': {
            'label': '批量情景模拟',
            'allowed_backends': ('python_loop', 'python_vectorized'),
            'allowed_modes': (
                'python_loop',
                'vectorized_python',
            ),
            'default_mode': 'vectorized_python',
            'default_backend': 'python_vectorized',
            'default_canary_percent': 100,
            'default_require_benchmark': False,
        },
    }

    _cached_policy: Dict[str, Any] | None = None
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
        ).document('compute_rollout')

    @staticmethod
    def _local_snapshot_path() -> Path:
        project_root = Path(__file__).resolve().parent.parent.parent
        return project_root / 'outputs' / 'compute_rollout_local.json'

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
            logger.warning('Failed to read local compute rollout snapshot: %s', exc)
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
    def _default_component_policy(cls, component: str) -> Dict[str, Any]:
        metadata = cls.COMPONENT_METADATA[component]
        return {
            'key': component,
            'label': metadata['label'],
            'rollout_mode': metadata['default_mode'],
            'preferred_backend': metadata['default_backend'],
            'canary_percent': metadata['default_canary_percent'],
            'require_benchmark': metadata['default_require_benchmark'],
            'last_benchmark_at': '',
            'last_benchmark_context': '',
            'last_benchmark_backend': '',
            'notes': '',
            'updated_at': '',
            'updated_by': 'system',
            'allowed_backends': list(metadata['allowed_backends']),
            'allowed_modes': list(metadata['allowed_modes']),
        }

    @classmethod
    def _default_policy(cls) -> Dict[str, Any]:
        return {
            'enabled': True,
            'updated_at': '',
            'updated_by': 'system',
            'components': {
                component: cls._default_component_policy(component)
                for component in cls.COMPONENT_METADATA
            },
        }

    @classmethod
    def _normalize_component_policy(
        cls,
        component: str,
        payload: Dict[str, Any] | None,
        *,
        base: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        metadata = cls.COMPONENT_METADATA[component]
        current = dict(base or cls._default_component_policy(component))
        incoming = dict(payload or {})

        rollout_mode = str(
            incoming.get('rollout_mode') or current.get('rollout_mode') or metadata['default_mode'],
        )
        if rollout_mode not in metadata['allowed_modes']:
            rollout_mode = metadata['default_mode']

        preferred_backend = str(
            incoming.get('preferred_backend')
            or current.get('preferred_backend')
            or metadata['default_backend'],
        )
        if preferred_backend not in metadata['allowed_backends']:
            preferred_backend = metadata['default_backend']

        canary_percent = incoming.get('canary_percent', current.get('canary_percent'))
        try:
            canary_percent = int(canary_percent)
        except Exception:
            canary_percent = metadata['default_canary_percent']
        canary_percent = max(0, min(100, canary_percent))

        require_benchmark = incoming.get(
            'require_benchmark',
            current.get('require_benchmark', metadata['default_require_benchmark']),
        )

        notes = str(incoming.get('notes') if 'notes' in incoming else current.get('notes') or '')
        updated_by = str(
            incoming.get('updated_by')
            or current.get('updated_by')
            or 'dashboard',
        )[:120]
        updated_at = str(incoming.get('updated_at') or current.get('updated_at') or '')

        last_benchmark_at = str(
            incoming.get('last_benchmark_at')
            or current.get('last_benchmark_at')
            or '',
        )
        last_benchmark_context = str(
            incoming.get('last_benchmark_context')
            or current.get('last_benchmark_context')
            or '',
        )
        last_benchmark_backend = str(
            incoming.get('last_benchmark_backend')
            or current.get('last_benchmark_backend')
            or '',
        )

        return {
            'key': component,
            'label': metadata['label'],
            'rollout_mode': rollout_mode,
            'preferred_backend': preferred_backend,
            'canary_percent': canary_percent,
            'require_benchmark': bool(require_benchmark),
            'last_benchmark_at': last_benchmark_at,
            'last_benchmark_context': last_benchmark_context,
            'last_benchmark_backend': last_benchmark_backend,
            'notes': notes[:240],
            'updated_at': updated_at,
            'updated_by': updated_by,
            'allowed_backends': list(metadata['allowed_backends']),
            'allowed_modes': list(metadata['allowed_modes']),
        }

    @classmethod
    def _normalize_policy(cls, payload: Dict[str, Any] | None) -> Dict[str, Any]:
        default_policy = cls._default_policy()
        incoming = dict(payload or {})
        components_payload = incoming.get('components')
        components_payload = (
            dict(components_payload)
            if isinstance(components_payload, dict)
            else {}
        )
        components: Dict[str, Any] = {}
        for component in cls.COMPONENT_METADATA:
            components[component] = cls._normalize_component_policy(
                component,
                components_payload.get(component) if isinstance(components_payload, dict) else None,
                base=default_policy['components'][component],
            )
        return {
            'enabled': bool(incoming.get('enabled', True)),
            'updated_at': str(incoming.get('updated_at') or ''),
            'updated_by': str(incoming.get('updated_by') or 'system')[:120],
            'components': components,
        }

    @classmethod
    def _set_cache(cls, policy: Dict[str, Any]) -> Dict[str, Any]:
        normalized = cls._normalize_policy(policy)
        cls._cached_policy = normalized
        cls._cached_at = time.time()
        return copy.deepcopy(normalized)

    @classmethod
    def get_policy(cls, *, force_refresh: bool = False) -> Dict[str, Any]:
        if (
            not force_refresh
            and cls._cached_policy is not None
            and (time.time() - cls._cached_at) <= cls.CACHE_TTL_S
        ):
            return copy.deepcopy(cls._cached_policy)

        try:
            snapshot = cls._doc_ref().get()
            raw = snapshot.to_dict() if snapshot.exists else {}
        except Exception as exc:
            logger.warning('Failed to load compute rollout policy from Firestore: %s', exc)
            raw = cls._load_local_snapshot()

        if not raw:
            raw = cls._default_policy()
        return cls._set_cache(raw)

    @classmethod
    def get_component_policy(
        cls,
        component: str,
        *,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        policy = cls.get_policy(force_refresh=force_refresh)
        component_policy = policy.get('components', {}).get(component)
        if isinstance(component_policy, dict):
            return component_policy
        if component in cls.COMPONENT_METADATA:
            return cls._default_component_policy(component)
        return {}

    @classmethod
    def serialize_policy(cls, policy: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = cls._normalize_policy(policy or cls.get_policy())
        components = payload.get('components')
        serialized_components = []
        if isinstance(components, dict):
            for component in cls.COMPONENT_METADATA:
                component_payload = components.get(component)
                if isinstance(component_payload, dict):
                    serialized_components.append(component_payload)
        return {
            'enabled': bool(payload.get('enabled')),
            'updated_at': str(payload.get('updated_at') or ''),
            'updated_by': str(payload.get('updated_by') or ''),
            'components': serialized_components,
        }

    @classmethod
    def update_policy(
        cls,
        *,
        components: Dict[str, Dict[str, Any]] | None = None,
        updated_by: str = 'dashboard',
    ) -> Dict[str, Any]:
        current = cls.get_policy(force_refresh=True)
        next_policy = copy.deepcopy(current)
        next_policy['updated_at'] = _utc_now_iso()
        next_policy['updated_by'] = str(updated_by or 'dashboard')[:120]

        for component, patch in dict(components or {}).items():
            if component not in cls.COMPONENT_METADATA or not isinstance(patch, dict):
                continue
            next_policy['components'][component] = cls._normalize_component_policy(
                component,
                {
                    **patch,
                    'updated_at': next_policy['updated_at'],
                    'updated_by': next_policy['updated_by'],
                },
                base=next_policy['components'].get(component),
            )

        try:
            cls._doc_ref().set(next_policy, merge=True)
        except Exception as exc:
            logger.warning('Failed to persist compute rollout policy: %s', exc)
            cls._write_local_snapshot(next_policy)
        return cls._set_cache(next_policy)

    @classmethod
    def record_benchmark(
        cls,
        component: str,
        *,
        context: str,
        backend: str,
        updated_by: str = 'benchmark',
    ) -> Dict[str, Any]:
        if component not in cls.COMPONENT_METADATA:
            return cls.get_policy()

        current = cls.get_policy(force_refresh=True)
        component_policy = current['components'][component]
        update_payload = {
            component: {
                'last_benchmark_at': _utc_now_iso(),
                'last_benchmark_context': str(context or ''),
                'last_benchmark_backend': str(backend or ''),
                'updated_by': updated_by,
                'updated_at': _utc_now_iso(),
            },
        }
        return cls.update_policy(components=update_payload, updated_by=updated_by)
