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
from services.compute_benchmark_gate_service import ComputeBenchmarkGateService

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
            'benchmark_status': 'pending',
            'benchmark_passed': False,
            'benchmark_summary': '',
            'benchmark_speedup_ratio': None,
            'benchmark_threshold': ComputeBenchmarkGateService._threshold_for(component),
            'benchmark_sample_rows': 0,
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
        benchmark_status = str(
            incoming.get('benchmark_status')
            or current.get('benchmark_status')
            or 'pending',
        )[:40]
        benchmark_passed = incoming.get(
            'benchmark_passed',
            current.get('benchmark_passed', False),
        )
        benchmark_summary = str(
            incoming.get('benchmark_summary')
            or current.get('benchmark_summary')
            or '',
        )[:240]
        benchmark_speedup_ratio = incoming.get(
            'benchmark_speedup_ratio',
            current.get('benchmark_speedup_ratio'),
        )
        try:
            benchmark_speedup_ratio = (
                round(float(benchmark_speedup_ratio), 3)
                if benchmark_speedup_ratio not in (None, '')
                else None
            )
        except Exception:
            benchmark_speedup_ratio = None
        benchmark_threshold = incoming.get(
            'benchmark_threshold',
            current.get('benchmark_threshold', ComputeBenchmarkGateService._threshold_for(component)),
        )
        try:
            benchmark_threshold = round(float(benchmark_threshold), 3)
        except Exception:
            benchmark_threshold = ComputeBenchmarkGateService._threshold_for(component)
        benchmark_sample_rows = incoming.get(
            'benchmark_sample_rows',
            current.get('benchmark_sample_rows', 0),
        )
        try:
            benchmark_sample_rows = max(0, int(benchmark_sample_rows))
        except Exception:
            benchmark_sample_rows = 0

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
            'benchmark_status': benchmark_status,
            'benchmark_passed': bool(benchmark_passed),
            'benchmark_summary': benchmark_summary,
            'benchmark_speedup_ratio': benchmark_speedup_ratio,
            'benchmark_threshold': benchmark_threshold,
            'benchmark_sample_rows': benchmark_sample_rows,
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
    def preview_component_policy(
        cls,
        component: str,
        patch: Dict[str, Any] | None = None,
        *,
        updated_by: str = 'preview',
    ) -> Dict[str, Any]:
        if component not in cls.COMPONENT_METADATA:
            return {}

        base = cls.get_component_policy(component, force_refresh=True)
        return cls._normalize_component_policy(
            component,
            {
                **dict(patch or {}),
                'updated_at': _utc_now_iso(),
                'updated_by': str(updated_by or 'preview')[:120],
            },
            base=base,
        )

    @classmethod
    def stable_rollout_mode(cls, component: str) -> str:
        metadata = cls.COMPONENT_METADATA.get(component) or {}
        return str(metadata.get('default_mode') or '')

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
        previous_summary = str(component_policy.get('benchmark_summary') or '')
        update_payload = {
            component: {
                **ComputeBenchmarkGateService.build_recorded_patch(
                    component,
                    context=context,
                    backend=backend,
                ),
                'benchmark_summary': previous_summary
                or 'Benchmark sample recorded; rerun governed benchmark for rollout admission',
                'updated_by': updated_by,
                'updated_at': _utc_now_iso(),
            },
        }
        return cls.update_policy(components=update_payload, updated_by=updated_by)

    @classmethod
    def record_benchmark_result(
        cls,
        component: str,
        *,
        context: str,
        backend: str,
        baseline_duration_ms: float | None,
        candidate_duration_ms: float | None,
        sample_rows: int = 0,
        error: str = '',
        updated_by: str = 'benchmark',
    ) -> Dict[str, Any]:
        if component not in cls.COMPONENT_METADATA:
            return cls.get_policy()

        update_payload = {
            component: {
                **ComputeBenchmarkGateService.build_policy_patch(
                    component,
                    context=context,
                    backend=backend,
                    baseline_duration_ms=baseline_duration_ms,
                    candidate_duration_ms=candidate_duration_ms,
                    sample_rows=sample_rows,
                    error=error,
                ),
                'updated_by': updated_by,
                'updated_at': _utc_now_iso(),
            },
        }
        return cls.update_policy(components=update_payload, updated_by=updated_by)
