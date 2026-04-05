"""Cross-worker compute capability probing."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List

from config import Config
from services.compute_worker_capability_service import ComputeWorkerCapabilityService

logger = logging.getLogger(__name__)


class ComputeRuntimeProbeService:
    """Read compute capability snapshots from local and heavy workers."""

    CACHE_TTL_S = 15.0
    _cached_targets: List[Dict[str, Any]] | None = None
    _cached_at = 0.0

    @classmethod
    def get_runtime_targets(cls) -> List[Dict[str, Any]]:
        if cls._cached_targets is not None and (time.time() - cls._cached_at) <= cls.CACHE_TTL_S:
            return [dict(target) for target in cls._cached_targets]

        targets = [
            ComputeWorkerCapabilityService.get_local_capability(worker_key='light_worker'),
        ]

        heavy_url = str(getattr(Config, 'HEAVY_SERVICE_URL', '') or '').strip().rstrip('/')
        if not heavy_url:
            targets.append(
                {
                    'worker_key': 'heavy_worker',
                    'worker_label': 'Heavy Worker',
                    'base_url': '',
                    'configured': False,
                    'reachable': False,
                    'native_enabled': False,
                    'native_available': False,
                    'preferred_backend': 'python_pandas',
                    'active_backend': 'python_pandas',
                    'module_name': '',
                    'status_reason': 'Heavy worker not configured',
                    'profile_enabled': False,
                }
            )
            cls._cached_targets = [dict(target) for target in targets]
            cls._cached_at = time.time()
            return [dict(target) for target in targets]

        targets.append(cls._fetch_remote_target(heavy_url))
        cls._cached_targets = [dict(target) for target in targets]
        cls._cached_at = time.time()
        return [dict(target) for target in targets]

    @classmethod
    def _fetch_remote_target(cls, base_url: str) -> Dict[str, Any]:
        request = urllib.request.Request(
            url=f'{base_url}/internal/runtime/worker-capability?worker_key=heavy_worker',
            headers={
                'Accept': 'application/json',
                'X-Internal-Job-Token': str(Config.INTERNAL_JOB_TOKEN or 'dev-internal-job-token'),
            },
            method='GET',
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=max(float(getattr(Config, 'ORCHESTRATOR_REQUEST_TIMEOUT_S', 10.0) or 10.0), 1.0),
            ) as response:
                body = response.read().decode('utf-8')
            payload = json.loads(body or '{}')
            data = payload.get('data') if isinstance(payload, dict) else {}
            if isinstance(data, dict):
                return {
                    **data,
                    'worker_key': 'heavy_worker',
                    'worker_label': 'Heavy Worker',
                    'base_url': base_url,
                    'configured': True,
                    'reachable': True,
                }
        except Exception as exc:
            logger.warning('Failed to probe heavy worker compute capability: %s', exc)
            return {
                'worker_key': 'heavy_worker',
                'worker_label': 'Heavy Worker',
                'base_url': base_url,
                'configured': True,
                'reachable': False,
                'native_enabled': False,
                'native_available': False,
                'preferred_backend': 'python_pandas',
                'active_backend': 'python_pandas',
                'module_name': '',
                'status_reason': f'Heavy worker probe failed: {exc}',
                'profile_enabled': False,
            }

        return {
            'worker_key': 'heavy_worker',
            'worker_label': 'Heavy Worker',
            'base_url': base_url,
            'configured': True,
            'reachable': False,
            'native_enabled': False,
            'native_available': False,
            'preferred_backend': 'python_pandas',
            'active_backend': 'python_pandas',
            'module_name': '',
            'status_reason': 'Heavy worker returned invalid capability payload',
            'profile_enabled': False,
        }
