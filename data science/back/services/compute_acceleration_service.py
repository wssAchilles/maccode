"""Profiling storage and dashboard summary for compute acceleration."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from google.cloud import firestore

from config import Config
from services.compute_governance_status_service import ComputeGovernanceStatusService
from services.compute_native_loader import get_native_backend_status
from services.compute_rollout_service import ComputeRolloutService

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


def _serialize_snapshot_item(item: Dict[str, Any]) -> Dict[str, Any]:
    serialized = dict(item)
    updated_at = serialized.get('last_updated_at')
    if isinstance(updated_at, datetime):
        serialized['last_updated_at'] = updated_at.isoformat()
    return serialized


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
        return firestore.Client(
            project=Config.GCP_PROJECT_ID,
            database=Config.FIRESTORE_DATABASE,
        )

    @classmethod
    def _collection(cls, client=None):
        client = client or cls._get_firestore_client()
        return client.collection(
            getattr(Config, 'COMPUTE_ACCELERATION_COLLECTION', 'compute_acceleration'),
        )

    @staticmethod
    def _local_snapshot_path() -> Path:
        project_root = Path(__file__).resolve().parent.parent.parent
        return project_root / 'outputs' / 'compute_acceleration_local.json'

    @classmethod
    def _load_local_snapshot(cls) -> Dict[str, Dict[str, Any]]:
        snapshot_path = cls._local_snapshot_path()
        if not snapshot_path.exists():
            return {}
        try:
            payload = json.loads(snapshot_path.read_text(encoding='utf-8'))
            if isinstance(payload, dict):
                return {
                    str(key): value
                    for key, value in payload.items()
                    if isinstance(value, dict)
                }
        except Exception as exc:
            logger.warning('Failed to read local compute snapshot: %s', exc)
        return {}

    @classmethod
    def _write_local_snapshot(cls, payload: Dict[str, Dict[str, Any]]) -> None:
        snapshot_path = cls._local_snapshot_path()
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding='utf-8',
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
    def _recent_status_window(cls, recent_durations: List[Any]) -> List[float]:
        window_size = max(1, int(getattr(Config, 'COMPUTE_STATUS_WINDOW', 5) or 5))
        normalized = [
            float(value)
            for value in list(recent_durations or [])
            if value is not None
        ]
        if not normalized:
            return []
        return normalized[-window_size:]

    @classmethod
    def _runtime_component_status(
        cls,
        *,
        component: str,
        last_duration_ms: float,
        avg_duration_ms: float,
        p95_duration_ms: float,
        recent_durations: List[Any],
        active_backend: str,
        native_enabled: bool,
        native_available: bool,
    ) -> str:
        threshold = cls._warning_threshold(component)
        error_budget = threshold * 1.6
        status_window = cls._recent_status_window(recent_durations)
        if native_enabled and not native_available:
            return 'warning'

        if not status_window:
            return cls._component_status(
                component=component,
                duration_ms=last_duration_ms,
                p95_duration_ms=p95_duration_ms,
                active_backend=active_backend,
                native_enabled=native_enabled,
                native_available=native_available,
            )

        latest_duration = float(status_window[-1])
        trailing_error_count = sum(
            value >= error_budget for value in status_window[-3:]
        )
        trailing_warning_count = sum(value >= threshold for value in status_window)
        window_p95 = cls._percentile(status_window, 95.0)
        window_avg = sum(status_window) / len(status_window)

        if latest_duration >= error_budget or trailing_error_count >= 2:
            return 'error'
        if (
            latest_duration >= threshold
            or trailing_warning_count >= 2
            or window_p95 >= error_budget
            or window_avg >= threshold
        ):
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
        if status in ('warning', 'error') and str(active_backend).startswith('python'):
            return '优先复核热点样本规模并运行 benchmark，再决定是否启用 C++ backend。'
        if status in ('warning', 'error'):
            return '热点计算已加速，但耗时仍偏高，建议继续做数据规模与窗口配置剖析。'
        if active_backend == 'native_cpp':
            return '当前热点已走 native backend，保持灰度监控即可。'
        return '当前热点运行平稳，继续保留 profiling 观测。'

    @classmethod
    def _build_component_payload(
        cls,
        *,
        component: str,
        label: str,
        current: Dict[str, Any],
        duration_ms: float,
        rows: int,
        backend: str,
        context: str,
        native_enabled: bool,
        native_available: bool,
        preferred_backend: str,
        metadata: Dict[str, Any],
        max_samples: int,
    ) -> Dict[str, Any]:
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
        return {
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
        skip_benchmark_marker: bool = False,
    ) -> None:
        """Persist a sampled hotspot invocation without breaking the caller."""

        if not bool(getattr(Config, 'COMPUTE_PROFILE_ENABLED', True)):
            return

        if not skip_benchmark_marker and 'benchmark' in str(context or '').lower():
            try:
                ComputeRolloutService.record_benchmark(
                    component,
                    context=context,
                    backend=backend,
                )
            except Exception as exc:
                logger.warning('Failed to update benchmark marker for %s: %s', component, exc)

        label = cls.COMPONENT_LABELS.get(component, component)
        metadata = dict(metadata or {})
        max_samples = int(getattr(Config, 'COMPUTE_PROFILE_WINDOW', 24) or 24)
        try:
            client = cls._get_firestore_client()
            doc_ref = cls._collection(client).document(component)
            snapshot = doc_ref.get()
            current = snapshot.to_dict() if snapshot.exists else _default_component_doc(component, label)
            payload = cls._build_component_payload(
                component=component,
                label=label,
                current=current,
                duration_ms=duration_ms,
                rows=rows,
                backend=backend,
                context=context,
                native_enabled=native_enabled,
                native_available=native_available,
                preferred_backend=preferred_backend,
                metadata=metadata,
                max_samples=max_samples,
            )
            doc_ref.set(payload, merge=True)
        except Exception as exc:
            logger.warning(
                'Failed to persist compute sample for %s: %s',
                component,
                exc,
            )
            local_snapshot = cls._load_local_snapshot()
            current = local_snapshot.get(component) or _default_component_doc(component, label)
            payload = cls._build_component_payload(
                component=component,
                label=label,
                current=current,
                duration_ms=duration_ms,
                rows=rows,
                backend=backend,
                context=context,
                native_enabled=native_enabled,
                native_available=native_available,
                preferred_backend=preferred_backend,
                metadata=metadata,
                max_samples=max_samples,
            )
            local_snapshot[component] = _serialize_snapshot_item(payload)
            cls._write_local_snapshot(local_snapshot)

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
            'rollout': ComputeGovernanceStatusService.get_policy_view(),
        }

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Build the compute acceleration summary used by the dashboard."""

        native_status = get_native_backend_status()
        base = cls.empty_status()
        rollout_policy = ComputeRolloutService.get_policy()
        source_label = 'firestore'
        try:
            client = cls._get_firestore_client()
            docs = [doc.to_dict() for doc in cls._collection(client).stream()]
        except Exception as exc:
            logger.warning('Failed to load compute acceleration status: %s', exc)
            local_snapshot = cls._load_local_snapshot()
            docs = list(local_snapshot.values())
            source_label = 'local'
            if not docs:
                return {
                    **base,
                    'status': 'warning',
                    'message': f'Compute acceleration telemetry unavailable: {exc}',
                }

        normalized_components: List[Dict[str, Any]] = []
        overall_status = 'info'
        last_updated_at = None
        rollout_refreshed = False
        for item in docs:
            if not item:
                continue
            component_key = str(item.get('component') or '')
            component_status = str(item.get('status') or 'info')
            updated_at = item.get('last_updated_at')
            if isinstance(updated_at, str):
                try:
                    updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                except Exception:
                    updated_at = None
            if isinstance(updated_at, datetime) and (
                last_updated_at is None or updated_at > last_updated_at
            ):
                last_updated_at = updated_at
            recent_durations = list(item.get('recent_durations_ms') or [])
            runtime_status = cls._runtime_component_status(
                component=component_key,
                last_duration_ms=float(item.get('last_duration_ms') or 0.0),
                avg_duration_ms=float(item.get('avg_duration_ms') or 0.0),
                p95_duration_ms=float(item.get('p95_duration_ms') or 0.0),
                recent_durations=recent_durations,
                active_backend=str(item.get('active_backend') or 'python_pandas'),
                native_enabled=bool(item.get('native_enabled')),
                native_available=bool(item.get('native_available')),
            )
            if cls.STATUS_ORDER.get(runtime_status, 0) > cls.STATUS_ORDER.get(overall_status, 0):
                overall_status = runtime_status
            contexts = list(item.get('contexts') or [])
            last_context = item.get('last_context') or ''
            benchmark_context = next(
                (
                    str(context)
                    for context in ([last_context] + contexts)
                    if 'benchmark' in str(context).lower()
                ),
                '',
            )
            rollout_component = (
                rollout_policy.get('components', {}).get(component_key)
                if isinstance(rollout_policy.get('components'), dict)
                else {}
            )
            if component_key and benchmark_context and isinstance(rollout_component, dict):
                if not str(rollout_component.get('last_benchmark_at') or ''):
                    rollout_policy = ComputeRolloutService.get_policy(force_refresh=True)
                    rollout_refreshed = True
                    rollout_component = (
                        rollout_policy.get('components', {}).get(component_key)
                        if isinstance(rollout_policy.get('components'), dict)
                        else {}
                    )
            if (
                component_key
                and benchmark_context
                and isinstance(rollout_component, dict)
                and cls._should_record_benchmark_sample(rollout_component)
            ):
                ComputeRolloutService.record_benchmark(
                    component_key,
                    context=benchmark_context,
                    backend=str(item.get('active_backend') or ''),
                    updated_by='telemetry_sync',
                )
                rollout_policy = ComputeRolloutService.get_policy(force_refresh=True)
                rollout_refreshed = True
            normalized_components.append(
                {
                    'key': component_key,
                    'label': item.get('label') or '--',
                    'status': runtime_status,
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
                    'recommended_action': cls._recommended_action(
                        status=runtime_status,
                        active_backend=str(item.get('active_backend') or 'python_pandas'),
                        native_enabled=bool(item.get('native_enabled')),
                        native_available=bool(item.get('native_available')),
                    ),
                }
            )

        normalized_components.sort(
            key=lambda item: (item['p95_duration_ms'], item['last_duration_ms']),
            reverse=True,
        )
        hottest_component = normalized_components[0]['label'] if normalized_components else '--'
        active_backend = (
            'native_cpp'
            if any(item.get('active_backend') == 'native_cpp' for item in normalized_components)
            else native_status.active_backend
        )

        rollout_payload = ComputeGovernanceStatusService.get_policy_view(
            rollout_policy if rollout_refreshed else None,
        )
        global_capability = cls._derive_global_runtime_capability(
            native_status=native_status,
            normalized_components=normalized_components,
            rollout_payload=rollout_payload,
        )

        if normalized_components:
            if overall_status == 'info':
                overall_status = 'ok'
        else:
            overall_status = 'info'

        message = cls._overall_message(
            overall_status=overall_status,
            active_backend=active_backend,
            source_label=source_label,
            normalized_components=normalized_components,
            global_native_enabled=bool(global_capability.get('native_enabled')),
            global_native_available=bool(global_capability.get('native_available')),
            native_status=native_status,
        )

        if (
            bool(global_capability.get('native_enabled'))
            and not bool(global_capability.get('native_available'))
            and active_backend != 'native_cpp'
        ):
            overall_status = 'warning'
            message = native_status.reason

        benchmark_ready = any(
            bool(component.get('benchmark_passed'))
            for component in rollout_payload.get('components', [])
            if isinstance(component, dict)
        )
        auto_rollback_components = [
            str(component.get('label') or '--')
            for component in rollout_payload.get('components', [])
            if isinstance(component, dict)
            and str(component.get('rollout_status') or '') == 'auto_rolled_back'
        ]
        if auto_rollback_components:
            overall_status = 'warning'
            message = (
                f'Compute guard auto-rolled back {auto_rollback_components[0]}'
                if len(auto_rollback_components) == 1
                else 'Compute guard auto-rolled back multiple components'
            )

        return {
            'enabled': bool(getattr(Config, 'COMPUTE_PROFILE_ENABLED', True)),
            'status': overall_status,
            'message': message,
            'preferred_backend': str(
                global_capability.get('preferred_backend') or native_status.preferred_backend,
            ),
            'active_backend': active_backend,
            'native_enabled': bool(global_capability.get('native_enabled')),
            'native_available': bool(global_capability.get('native_available')),
            'profiled_components': len(normalized_components),
            'benchmark_ready': benchmark_ready,
            'hottest_component': hottest_component,
            'last_updated_at': last_updated_at.isoformat() if isinstance(last_updated_at, datetime) else '',
            'components': normalized_components[:4],
            'rollout': rollout_payload,
        }

    @staticmethod
    def _derive_global_runtime_capability(
        *,
        native_status: Any,
        normalized_components: List[Dict[str, Any]],
        rollout_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        runtime_targets = [
            dict(target)
            for target in (rollout_payload.get('runtime_targets') or [])
            if isinstance(target, dict)
        ]
        native_enabled = any(bool(target.get('native_enabled')) for target in runtime_targets) or any(
            bool(item.get('native_enabled'))
            for item in normalized_components
        )
        native_available = any(
            bool(target.get('native_available'))
            for target in runtime_targets
        ) or any(bool(item.get('native_available')) for item in normalized_components)
        preferred_backend = native_status.preferred_backend
        if any(
            str(target.get('preferred_backend') or '') == 'native_cpp'
            for target in runtime_targets
        ) or any(
            str(item.get('preferred_backend') or '') == 'native_cpp'
            for item in normalized_components
        ):
            preferred_backend = 'native_cpp'
        return {
            'native_enabled': native_enabled,
            'native_available': native_available,
            'preferred_backend': preferred_backend,
        }

    @staticmethod
    def _overall_message(
        *,
        overall_status: str,
        active_backend: str,
        source_label: str,
        normalized_components: List[Dict[str, Any]],
        global_native_enabled: bool,
        global_native_available: bool,
        native_status: Any,
    ) -> str:
        if not normalized_components:
            return 'Compute acceleration telemetry is waiting for the first hotspot sample'

        hottest = normalized_components[0]
        hottest_label = str(hottest.get('label') or '--')
        recommended_action = str(hottest.get('recommended_action') or '').strip()
        hottest_status = str(hottest.get('status') or 'info')

        if source_label == 'local':
            return 'Compute acceleration telemetry active (local snapshot)'
        if overall_status == 'error':
            return f'{hottest_label} latency is still over budget'
        if overall_status == 'warning':
            if global_native_enabled and not global_native_available:
                return native_status.reason
            if hottest_status == 'warning':
                return f'{hottest_label} shows recent latency spikes'
            if recommended_action:
                return recommended_action
        if active_backend == 'native_cpp':
            return 'Native compute backend is active'
        return 'Compute acceleration telemetry active'

    @staticmethod
    def _should_record_benchmark_sample(component_policy: Dict[str, Any]) -> bool:
        """Only backfill a recorded benchmark marker when no governed result exists."""

        if str(component_policy.get('last_benchmark_at') or '').strip():
            return False
        benchmark_status = str(component_policy.get('benchmark_status') or '').strip().lower()
        benchmark_summary = str(component_policy.get('benchmark_summary') or '').strip()
        if benchmark_status and benchmark_status != 'pending':
            return False
        if benchmark_summary:
            return False
        return True
