"""Backend selection for compute hotspots."""

from __future__ import annotations

import hashlib
from typing import Any, Dict

from services.compute_native_loader import get_native_backend_status
from services.compute_rollout_service import ComputeRolloutService


def _bucket_for_seed(seed: str) -> int:
    digest = hashlib.sha1(seed.encode('utf-8')).hexdigest()
    return int(digest[:8], 16) % 100


def select_feature_engineering_backend(context: str = '') -> Dict[str, Any]:
    policy = ComputeRolloutService.get_component_policy('feature_engineering')
    native_status = get_native_backend_status()
    benchmark_ready = bool(policy.get('last_benchmark_at'))
    require_benchmark = bool(policy.get('require_benchmark'))
    rollout_mode = str(policy.get('rollout_mode') or 'python_stable')
    canary_percent = int(policy.get('canary_percent') or 0)
    preferred_backend = str(policy.get('preferred_backend') or 'python_pandas')

    if rollout_mode == 'python_stable':
        return {
            'backend': 'python_pandas',
            'rollout_mode': rollout_mode,
            'rollout_reason': 'rollout policy keeps Python stable path',
            'preferred_backend': preferred_backend,
            'canary_percent': canary_percent,
            'benchmark_ready': benchmark_ready,
            'native_enabled': native_status.native_enabled,
            'native_available': native_status.native_available,
            'module_name': native_status.module_name,
        }

    if not native_status.native_enabled:
        return {
            'backend': 'python_pandas',
            'rollout_mode': rollout_mode,
            'rollout_reason': 'native backend disabled by environment',
            'preferred_backend': preferred_backend,
            'canary_percent': canary_percent,
            'benchmark_ready': benchmark_ready,
            'native_enabled': native_status.native_enabled,
            'native_available': native_status.native_available,
            'module_name': native_status.module_name,
        }

    if not native_status.native_available:
        return {
            'backend': 'python_pandas',
            'rollout_mode': rollout_mode,
            'rollout_reason': 'native module not available on this worker',
            'preferred_backend': preferred_backend,
            'canary_percent': canary_percent,
            'benchmark_ready': benchmark_ready,
            'native_enabled': native_status.native_enabled,
            'native_available': native_status.native_available,
            'module_name': native_status.module_name,
        }

    if require_benchmark and not benchmark_ready:
        return {
            'backend': 'python_pandas',
            'rollout_mode': rollout_mode,
            'rollout_reason': 'benchmark gate not satisfied for native rollout',
            'preferred_backend': preferred_backend,
            'canary_percent': canary_percent,
            'benchmark_ready': benchmark_ready,
            'native_enabled': native_status.native_enabled,
            'native_available': native_status.native_available,
            'module_name': native_status.module_name,
        }

    if rollout_mode == 'native_enforced':
        return {
            'backend': 'native_cpp',
            'rollout_mode': rollout_mode,
            'rollout_reason': 'native backend enforced by rollout policy',
            'preferred_backend': preferred_backend,
            'canary_percent': canary_percent,
            'benchmark_ready': benchmark_ready,
            'native_enabled': native_status.native_enabled,
            'native_available': native_status.native_available,
            'module_name': native_status.module_name,
        }

    seed = context or 'feature_engineering'
    bucket = _bucket_for_seed(f'feature_engineering:{seed}')
    if bucket < canary_percent:
        return {
            'backend': 'native_cpp',
            'rollout_mode': rollout_mode,
            'rollout_reason': f'canary bucket {bucket} matched threshold {canary_percent}',
            'preferred_backend': preferred_backend,
            'canary_percent': canary_percent,
            'benchmark_ready': benchmark_ready,
            'native_enabled': native_status.native_enabled,
            'native_available': native_status.native_available,
            'module_name': native_status.module_name,
        }

    return {
        'backend': 'python_pandas',
        'rollout_mode': rollout_mode,
        'rollout_reason': f'canary bucket {bucket} outside threshold {canary_percent}',
        'preferred_backend': preferred_backend,
        'canary_percent': canary_percent,
        'benchmark_ready': benchmark_ready,
        'native_enabled': native_status.native_enabled,
        'native_available': native_status.native_available,
        'module_name': native_status.module_name,
    }


def select_scenario_simulation_backend(context: str = '') -> Dict[str, Any]:
    policy = ComputeRolloutService.get_component_policy('scenario_simulation')
    rollout_mode = str(policy.get('rollout_mode') or 'vectorized_python')
    preferred_backend = str(policy.get('preferred_backend') or 'python_vectorized')
    backend = 'python_vectorized' if rollout_mode == 'vectorized_python' else 'python_loop'
    return {
        'backend': backend,
        'rollout_mode': rollout_mode,
        'rollout_reason': 'vectorized scenario backend active'
        if backend == 'python_vectorized'
        else 'loop scenario backend pinned by rollout policy',
        'preferred_backend': preferred_backend,
        'canary_percent': int(policy.get('canary_percent') or 100),
        'benchmark_ready': bool(policy.get('last_benchmark_at')),
        'native_enabled': False,
        'native_available': False,
        'module_name': '',
    }
