"""Control-plane runtime telemetry for dashboard surfaces."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict

from config import Config


def _default_lane(capacity: int = 0) -> Dict[str, Any]:
    return {
        'capacity': capacity,
        'available': capacity,
        'in_use': 0,
    }


def _default_compute_acceleration() -> Dict[str, Any]:
    return {
        'status': 'info',
        'message': 'Compute telemetry not linked',
        'active_backend': 'python_pandas',
        'preferred_backend': 'python_pandas',
        'native_enabled': False,
        'native_available': False,
        'profiled_components': 0,
        'benchmark_ready': False,
        'hottest_component': '--',
        'last_updated_at': '',
    }


def _default_compute_rollout() -> Dict[str, Any]:
    return {
        'enabled': False,
        'updated_at': '',
        'updated_by': '',
        'components': [],
    }


class ControlPlaneStatusService:
    """Fetch and normalize orchestrator/control-plane health."""

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        orchestrator_url = str(Config.ORCHESTRATOR_BASE_URL or '').strip().rstrip('/')
        configured_light = int(getattr(Config, 'ORCHESTRATOR_MAX_LIGHT_PARALLEL', 4) or 4)
        configured_heavy = int(getattr(Config, 'ORCHESTRATOR_MAX_HEAVY_PARALLEL', 2) or 2)
        configured_dispatch_timeout = int(
            getattr(Config, 'ORCHESTRATOR_DISPATCH_TIMEOUT_S', 1800) or 1800,
        )
        base_status: Dict[str, Any] = {
            'enabled': bool(orchestrator_url),
            'execution_mode': Config.TASKS_EXECUTION_MODE,
            'orchestrator_url': orchestrator_url,
            'dispatch_timeout_s': configured_dispatch_timeout,
            'status': 'warning' if orchestrator_url else 'info',
            'message': 'Rust orchestrator not configured'
            if not orchestrator_url
            else 'Rust orchestrator configured',
            'active_operations': 0,
            'python_worker_configured': False,
            'light_lane': _default_lane(configured_light),
            'heavy_lane': _default_lane(configured_heavy),
            'compute_acceleration': _default_compute_acceleration(),
            'compute_rollout': _default_compute_rollout(),
        }

        if not orchestrator_url:
            return base_status

        try:
            payload = cls._fetch_status_payload(orchestrator_url)
            light_lane = dict(payload.get('light_lane') or {})
            heavy_lane = dict(payload.get('heavy_lane') or {})
            return {
                **base_status,
                'status': 'ok',
                'message': cls._build_status_message(payload),
                'active_operations': int(payload.get('active_operations') or 0),
                'python_worker_configured': bool(payload.get('python_worker_configured')),
                'dispatch_timeout_s': int(payload.get('dispatch_timeout_secs') or 0)
                or Config.ORCHESTRATOR_REQUEST_TIMEOUT_S,
                'light_lane': {
                    **_default_lane(),
                    **light_lane,
                },
                'heavy_lane': {
                    **_default_lane(),
                    **heavy_lane,
                },
                'compute_acceleration': {
                    **_default_compute_acceleration(),
                    **dict(payload.get('compute_acceleration') or {}),
                },
                'compute_rollout': {
                    **_default_compute_rollout(),
                    **dict(payload.get('compute_rollout') or {}),
                },
            }
        except Exception as exc:
            try:
                cls._verify_ready(orchestrator_url)
                return {
                    **base_status,
                    'status': 'ok',
                    'message': 'Rust orchestrator ready (config-derived lane budget)',
                    'python_worker_configured': True,
                }
            except Exception:
                pass
            return {
                **base_status,
                'status': 'error',
                'message': f'Rust orchestrator unreachable: {exc}',
            }

    @staticmethod
    def _build_status_message(payload: Dict[str, Any]) -> str:
        compute = payload.get('compute_acceleration')
        if not isinstance(compute, dict):
            return 'Rust orchestrator ready'

        active_backend = str(compute.get('active_backend') or 'python_pandas')
        hottest = str(compute.get('hottest_component') or '--')
        profiled_components = int(compute.get('profiled_components') or 0)
        if profiled_components <= 0:
            return 'Rust orchestrator ready · compute telemetry waiting for samples'
        return f'Rust orchestrator ready · compute {active_backend} · hottest {hottest}'

    @staticmethod
    def _fetch_status_payload(orchestrator_url: str) -> Dict[str, Any]:
        last_error: Exception | None = None
        for path in ('/statusz', '/readyz'):
            request = urllib.request.Request(
                f'{orchestrator_url}{path}',
                headers={'Accept': 'application/json'},
                method='GET',
            )
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=max(float(Config.ORCHESTRATOR_REQUEST_TIMEOUT_S), 1.0),
                ) as response:
                    body = response.read().decode('utf-8')
                payload = json.loads(body or '{}')
                if isinstance(payload, dict):
                    return payload
                raise ValueError('invalid orchestrator status payload')
            except Exception as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise ValueError('orchestrator status payload unavailable')

    @staticmethod
    def _verify_ready(orchestrator_url: str) -> None:
        request = urllib.request.Request(
            f'{orchestrator_url}/readyz',
            headers={'Accept': 'application/json'},
            method='GET',
        )
        with urllib.request.urlopen(
            request,
            timeout=max(float(Config.ORCHESTRATOR_REQUEST_TIMEOUT_S), 1.0),
        ) as response:
            if response.status >= 400:
                raise urllib.error.HTTPError(
                    request.full_url,
                    response.status,
                    'readyz returned non-success',
                    response.headers,
                    None,
                )
