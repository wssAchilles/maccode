"""Worker-local compute capability snapshots."""

from __future__ import annotations

from typing import Any, Dict

from config import Config
from services.compute_native_loader import get_native_backend_status


class ComputeWorkerCapabilityService:
    """Expose the local worker's compute capability without full dashboard state."""

    @staticmethod
    def get_local_capability(*, worker_key: str = 'light_worker') -> Dict[str, Any]:
        native_status = get_native_backend_status()
        return {
            'worker_key': worker_key,
            'worker_label': 'Light Worker'
            if worker_key == 'light_worker'
            else 'Heavy Worker',
            'base_url': str(
                Config.INTERNAL_BASE_URL
                if worker_key == 'light_worker'
                else Config.HEAVY_SERVICE_URL or '',
            ).strip(),
            'configured': True,
            'reachable': True,
            'native_enabled': native_status.native_enabled,
            'native_available': native_status.native_available,
            'preferred_backend': native_status.preferred_backend,
            'active_backend': native_status.active_backend,
            'module_name': native_status.module_name,
            'status_reason': native_status.reason,
            'profile_enabled': bool(getattr(Config, 'COMPUTE_PROFILE_ENABLED', True)),
        }
