"""Profiling storage and dashboard summary for compute acceleration."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from google.cloud import firestore

from config import Config
from services.compute_native_loader import get_native_backend_status

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _default_component_doc(component: str, label: str) -> Dict[str, Any]:
    return {
        'component': component,
        'label': label,
        'status': 'info',
        'active_backend': 'python_pandas',
        'native_enabled': False,
        'native_available': False,
        'preferred_backend': 'python_pandas',
        'invocation_count': 0,
        'last_duration_ms': 0.0,
        'avg_duration_ms': 0.0,
        'p95_duration_ms': 0.0,
        'recent_durations_ms': [],
        'contexts': [],
        'last_context': '',
        'last_rows': 0,
        'last_updated_at': None,
        'recommended_action': '保持监控',
        'metadata': {},
    }


class ComputeAccelerationService:
    """Persist compute hotspot telemetry and build dashboard-ready summaries."""

    COMPONENT_LABELS = {
        'feature_engineering': '高级特征工程',
        'scenario_simulation': '批量情景模拟',
    }

    COMPONENT_WARNING_MS = {
        'feature_engineering': 200.0,
        'scenario_simulation': 450.0,
    }

    STATUS_ORDER = {
        'error': 3,
        'warning': 2,
        'ok': 1,
        'info': 0,
    }

    @staticmethod
    def _get_firestore_client():
        return firestore.Client(database=Config.FIRESTORE_DATABASE)

    @classmethod
    def _collection(cls):
        return cls._get_firestore_client().collection(
            getattr(Config, 'COMPUTE_ACCELERATION_COLLECTION', 'compute_acceleration'),
        )

    @classmethod
    def _warning_threshold(cls, component: str) -> float:
        return float(
            getattr(Config, 'COMPUTE_FEATURE_WARNING_MS', cls.COMPONENT_WARNING_MS['feature_engineering'])
            if component == 'feature_engineering'
            else getattr(Config, 'COMPUTE_SCENARIO_WARNING_MS', cls.COMPONENT_WARNING_MS['scenario_simulation']),
        )

    @staticmethod
    def _percentile(values: List[float], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(float(value) for value in values if value is not None)
        if not ordered:
            return 0.0
        if len(ordered) == 1:
            return float(ordered[0])
        index = max(0, min(len(ordered) - 1, round((percentile / 100.0) * (len(ordered) - 1))))
        return float(ordered[index])

    @classmethod
    def _component_status(
        cls,
        *,
        component: str,
        duration_ms: float,
        p95_duration_ms: float,
        active_backend: str,
        native_enabled: bool,
        native_available: bool,
    ) -> str:
        threshold = cls._warning_threshold(component)
        if native_enabled and not native_available:
            return 'warning'
        if duration_ms >= threshold * 1.6 or p95_duration_ms >= threshold * 1.6:
            return 'error'
        if duration_ms >= threshold or p95_duration_ms >= threshold:
            return 'warning'
        if active_backend:
            return 'ok'
        return 'info'

    @classmethod
    def _recommended_action(
        cls,
        *,
        status: str,
        active_backend: str,
        native_enabled: bool,
        native_available: bool,
    ) -> str:
        if native_enabled and not native_available:
            return '本地 native 模块未安装，继续使用 Python fallback 并按需构建 C++ 插件。'
        if status in ('warning', 'error') and active_backend == 'python_pandas':
            return '优先复核热点样本规模并运行 benchmark，再决定是否启用 C++ backend。'
        if status in ('warning', 'error'):
            return '热点计算已加速，但耗时仍偏高，建议继续做数据规模与窗口配置剖析。'
        if active_backend == 'native_cpp':
            return '当前热点已走 native backend，保持灰度监控即可。'
        return '当前热点运行平稳，继续保留 profiling 观测。'

    @classmethod
    def record_component_sample(
        cls,
        *,
        component: str,
        duration_ms: float,
        rows: int = 0,
        backend: str = 'python_pandas',
        context: str = '',
        native_enabled: bool = False,
        native_available: bool = False,
        preferred_backend: str = 'python_pandas',
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        """Persist a sampled hotspot invocation without breaking the caller."""

        if not bool(getattr(Config, 'COMPUTE_PROFILE_ENABLED', True)):
            return

        label = cls.COMPONENT_LABELS.get(component, component)
        metadata = dict(metadata or {})
        max_samples = int(getattr(Config, 'COMPUTE_PROFILE_WINDOW', 24) or 24)
        doc_ref = cls._collection().document(component)
        transaction = cls._get_firestore_client().transaction()

        @firestore.transactional
        def _update(transaction):
            snapshot = doc_ref.get(transaction=transaction)
            current = snapshot.to_dict() if snapshot.exists else _default_component_doc(component, label)
            recent_durations = list(current.get('recent_durations_ms') or [])
            recent_durations.append(float(duration_ms))
            recent_durations = recent_durations[-max_samples:]

            previous_count = int(current.get('invocation_count') or 0)
            invocation_count = previous_count + 1
            previous_avg = float(current.get('avg_duration_ms') or 0.0)
            avg_duration_ms = (
                (previous_avg * previous_count) + float(duration_ms)
            ) / invocation_count
            p95_duration_ms = cls._percentile(recent_durations, 95.0)

            contexts = list(current.get('contexts') or [])
            if context:
                contexts = [item for item in contexts if item != context]
                contexts.append(context)
                contexts = contexts[-6:]

            component_status = cls._component_status(
                component=component,
                duration_ms=float(duration_ms),
                p95_duration_ms=p95_duration_ms,
                active_backend=backend,
                native_enabled=native_enabled,
                native_available=native_available,
            )
            payload = {
                'component': component,
                'label': label,
                'status': component_status,
                'active_backend': backend,
                'native_enabled': bool(native_enabled),
                'native_available': bool(native_available),
                'preferred_backend': preferred_backend,
                'invocation_count': invocation_count,
                'last_duration_ms': round(float(duration_ms), 3),
                'avg_duration_ms': round(float(avg_duration_ms), 3),
                'p95_duration_ms': round(float(p95_duration_ms), 3),
                'recent_durations_ms': [round(float(value), 3) for value in recent_durations],
                'contexts': contexts,
                'last_context': context,
                'last_rows': int(rows or 0),
                'last_updated_at': _utc_now(),
                'recommended_action': cls._recommended_action(
                    status=component_status,
                    active_backend=backend,
                    native_enabled=native_enabled,
                    native_available=native_available,
                ),
                'metadata': metadata,
            }
            transaction.set(doc_ref, payload, merge=True)

        try:
            _update(transaction)
        except Exception as exc:
            logger.warning(
                'Failed to persist compute sample for %s: %s',
                component,
                exc,
                exc_info=True,
            )

    @classmethod
    def empty_status(cls) -> Dict[str, Any]:
        native_status = get_native_backend_status()
        return {
            'enabled': bool(getattr(Config, 'COMPUTE_PROFILE_ENABLED', True)),
            'status': 'info',
            'message': 'Compute acceleration telemetry is not available yet',
            'preferred_backend': native_status.preferred_backend,
            'active_backend': native_status.active_backend,
            'native_enabled': native_status.native_enabled,
            'native_available': native_status.native_available,
            'profiled_components': 0,
            'benchmark_ready': False,
            'hottest_component': '--',
            'last_updated_at': '',
            'components': [],
        }

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Build the compute acceleration summary used by the dashboard."""

        native_status = get_native_backend_status()
        base = cls.empty_status()
        try:
            docs = [doc.to_dict() for doc in cls._collection().stream()]
        except Exception as exc:
            logger.warning('Failed to load compute acceleration status: %s', exc, exc_info=True)
            return {
                **base,
                'status': 'warning',
                'message': f'Compute acceleration telemetry unavailable: {exc}',
            }

        normalized_components: List[Dict[str, Any]] = []
        overall_status = 'info'
        last_updated_at = None
        for item in docs:
            if not item:
                continue
            component_status = str(item.get('status') or 'info')
            if cls.STATUS_ORDER.get(component_status, 0) > cls.STATUS_ORDER.get(overall_status, 0):
                overall_status = component_status
            updated_at = item.get('last_updated_at')
            if isinstance(updated_at, datetime) and (
                last_updated_at is None or updated_at > last_updated_at
            ):
                last_updated_at = updated_at
            normalized_components.append(
                {
                    'key': item.get('component') or '',
                    'label': item.get('label') or '--',
                    'status': component_status,
                    'active_backend': item.get('active_backend') or 'python_pandas',
                    'preferred_backend': item.get('preferred_backend') or native_status.preferred_backend,
                    'native_enabled': bool(item.get('native_enabled')),
                    'native_available': bool(item.get('native_available')),
                    'last_duration_ms': float(item.get('last_duration_ms') or 0.0),
                    'avg_duration_ms': float(item.get('avg_duration_ms') or 0.0),
                    'p95_duration_ms': float(item.get('p95_duration_ms') or 0.0),
                    'invocation_count': int(item.get('invocation_count') or 0),
                    'last_rows': int(item.get('last_rows') or 0),
                    'last_context': item.get('last_context') or '',
                    'contexts': list(item.get('contexts') or []),
                    'recommended_action': item.get('recommended_action') or '保持监控',
                }
            )

        normalized_components.sort(
            key=lambda item: (item['p95_duration_ms'], item['last_duration_ms']),
            reverse=True,
        )
        hottest_component = normalized_components[0]['label'] if normalized_components else '--'
        benchmark_ready = any(
            'benchmark' in str(component.get('last_context') or '')
            or any('benchmark' in str(ctx) for ctx in component.get('contexts') or [])
            for component in normalized_components
        )
        active_backend = (
            'native_cpp'
            if any(item.get('active_backend') == 'native_cpp' for item in normalized_components)
            else native_status.active_backend
        )

        if normalized_components:
            if overall_status == 'info':
                overall_status = 'ok'
            message = (
                'Compute acceleration telemetry active'
                if active_backend == 'python_pandas'
                else 'Native compute backend is active'
            )
        else:
            overall_status = 'info'
            message = 'Compute acceleration telemetry is waiting for the first hotspot sample'

        if native_status.native_enabled and not native_status.native_available:
            overall_status = 'warning'
            message = native_status.reason

        return {
            'enabled': bool(getattr(Config, 'COMPUTE_PROFILE_ENABLED', True)),
            'status': overall_status,
            'message': message,
            'preferred_backend': native_status.preferred_backend,
            'active_backend': active_backend,
            'native_enabled': native_status.native_enabled,
            'native_available': native_status.native_available,
            'profiled_components': len(normalized_components),
            'benchmark_ready': benchmark_ready,
            'hottest_component': hottest_component,
            'last_updated_at': last_updated_at.isoformat() if isinstance(last_updated_at, datetime) else '',
            'components': normalized_components[:4],
        }

