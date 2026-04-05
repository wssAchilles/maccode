"""Structured compute benchmark workflows for governance operations."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Dict, List, Sequence

import numpy as np
import pandas as pd

from services.compute_acceleration_service import ComputeAccelerationService
from services.compute_benchmark_gate_service import ComputeBenchmarkGateService
from services.compute_native_loader import get_native_backend_status
from services.compute_rollout_service import ComputeRolloutService
from services.data_processor import EnergyDataProcessor
from services.feature_kernels import _native_load_features, _python_load_features
from services.scenario_kernels import (
    expand_variations,
    simulate_scenarios_loop,
    simulate_scenarios_vectorized,
)
from utils.exceptions import ValidationError


class ComputeBenchmarkService:
    """Run safe benchmark workloads for rollout governance."""

    DEFAULT_ROWS = 5000

    @classmethod
    def run(
        cls,
        payload: Dict[str, Any] | None = None,
        *,
        operation_id: str = '',
    ) -> Dict[str, Any]:
        payload = dict(payload or {})
        component = str(payload.get('component') or '').strip()
        if component == 'feature_engineering':
            return cls._run_feature_engineering_benchmark(payload, operation_id=operation_id)
        if component == 'scenario_simulation':
            return cls._run_scenario_benchmark(payload, operation_id=operation_id)
        raise ValidationError('不支持的 benchmark 组件')

    @classmethod
    def _run_feature_engineering_benchmark(
        cls,
        payload: Dict[str, Any],
        *,
        operation_id: str,
    ) -> Dict[str, Any]:
        frame = cls._sample_frame(int(payload.get('sample_rows') or cls.DEFAULT_ROWS))
        processor = EnergyDataProcessor()
        frame = processor.add_enhanced_time_features(frame)
        site_load = frame['Site_Load'].astype(float)

        python_started = perf_counter()
        _python_load_features(site_load)
        python_duration_ms = (perf_counter() - python_started) * 1000.0

        native_status = get_native_backend_status()
        native_duration_ms = None
        native_error = ''
        if native_status.native_enabled and native_status.native_available:
            native_started = perf_counter()
            try:
                _native_load_features(site_load)
                native_duration_ms = (perf_counter() - native_started) * 1000.0
            except Exception as exc:
                native_error = str(exc)

        context = f'benchmark_feature_engineering:{operation_id or "manual"}'
        active_backend = 'native_cpp' if native_duration_ms is not None else 'python_pandas'
        sampled_duration = native_duration_ms if native_duration_ms is not None else python_duration_ms
        gate_patch = ComputeBenchmarkGateService.build_policy_patch(
            'feature_engineering',
            context=context,
            backend=active_backend,
            baseline_duration_ms=python_duration_ms,
            candidate_duration_ms=native_duration_ms,
            sample_rows=len(frame),
            error=native_error,
        )
        ComputeRolloutService.record_benchmark_result(
            'feature_engineering',
            context=context,
            backend=active_backend,
            baseline_duration_ms=python_duration_ms,
            candidate_duration_ms=native_duration_ms,
            sample_rows=len(frame),
            error=native_error,
        )

        ComputeAccelerationService.record_component_sample(
            component='feature_engineering',
            duration_ms=sampled_duration,
            rows=len(frame),
            backend=active_backend,
            context=context,
            native_enabled=native_status.native_enabled,
            native_available=native_status.native_available,
            preferred_backend='native_cpp'
            if native_status.native_enabled
            else 'python_pandas',
            metadata={
                'python_duration_ms': round(python_duration_ms, 3),
                'native_duration_ms': round(native_duration_ms, 3)
                if native_duration_ms is not None
                else None,
                'native_error': native_error,
                'sample_rows': len(frame),
            },
            skip_benchmark_marker=True,
        )

        speedup_ratio = (
            round(python_duration_ms / native_duration_ms, 3)
            if native_duration_ms not in (None, 0)
            else None
        )
        summary = str(gate_patch.get('benchmark_summary') or '')

        return {
            'component': 'feature_engineering',
            'component_label': '高级特征工程',
            'summary': summary,
            'artifacts': [
                {
                    'type': 'benchmark_report',
                    'name': '高级特征工程 benchmark',
                    'uri': f'benchmark://feature_engineering/{operation_id or "manual"}',
                    'metadata': {
                        'python_duration_ms': round(python_duration_ms, 3),
                        'native_duration_ms': round(native_duration_ms, 3)
                        if native_duration_ms is not None
                        else None,
                        'speedup_ratio': speedup_ratio,
                    },
                }
            ],
            'metrics': {
                'benchmark_component': 'feature_engineering',
                'benchmark_backend': active_backend,
                'python_duration_ms': round(python_duration_ms, 3),
                'native_duration_ms': round(native_duration_ms, 3)
                if native_duration_ms is not None
                else None,
                'speedup_ratio': speedup_ratio,
                'native_error': native_error,
                'compute_metrics': {
                    'feature_engineering': {
                        'backend': active_backend,
                        'duration_ms': round(sampled_duration, 3),
                        'input_rows': len(frame),
                        'context': context,
                        'native_enabled': native_status.native_enabled,
                        'native_available': native_status.native_available,
                        'module_name': native_status.module_name,
                        'fallback_reason': native_error,
                        'rollout_mode': 'benchmark',
                        'rollout_reason': summary,
                        'benchmark_ready': bool(gate_patch.get('benchmark_passed')),
                        'benchmark_status': str(gate_patch.get('benchmark_status') or ''),
                        'benchmark_summary': summary,
                        'benchmark_speedup_ratio': gate_patch.get('benchmark_speedup_ratio'),
                    }
                },
            },
            'result': {
                'python_duration_ms': round(python_duration_ms, 3),
                'native_duration_ms': round(native_duration_ms, 3)
                if native_duration_ms is not None
                else None,
                'speedup_ratio': speedup_ratio,
                'native_available': native_status.native_available,
                'native_enabled': native_status.native_enabled,
                'native_error': native_error,
            },
        }

    @classmethod
    def _run_scenario_benchmark(
        cls,
        payload: Dict[str, Any],
        *,
        operation_id: str,
    ) -> Dict[str, Any]:
        frame = cls._sample_frame(int(payload.get('sample_rows') or 48))
        load_profile = frame['Site_Load'].tail(24).astype(float).tolist()
        price_profile = frame['Price'].tail(24).astype(float).tolist()
        _, scenario_params = expand_variations(
            {
                'battery_capacity': [50, 100, 150],
                'max_power': [20, 40, 60],
            },
            base_battery_capacity=100,
            base_max_power=40,
        )

        vector_started = perf_counter()
        vector_results = simulate_scenarios_vectorized(
            load_profile=load_profile,
            price_profile=price_profile,
            scenario_params=scenario_params,
            base_battery_capacity=100,
            base_max_power=40,
            efficiency=0.95,
            initial_soc=0.5,
        )
        vector_duration_ms = (perf_counter() - vector_started) * 1000.0

        loop_started = perf_counter()
        simulate_scenarios_loop(
            load_profile=load_profile,
            price_profile=price_profile,
            scenario_params=scenario_params,
            base_battery_capacity=100,
            base_max_power=40,
            efficiency=0.95,
            initial_soc=0.5,
        )
        loop_duration_ms = (perf_counter() - loop_started) * 1000.0

        context = f'benchmark_scenario_simulation:{operation_id or "manual"}'
        gate_patch = ComputeBenchmarkGateService.build_policy_patch(
            'scenario_simulation',
            context=context,
            backend='python_vectorized',
            baseline_duration_ms=loop_duration_ms,
            candidate_duration_ms=vector_duration_ms,
            sample_rows=len(vector_results),
        )
        ComputeRolloutService.record_benchmark_result(
            'scenario_simulation',
            context=context,
            backend='python_vectorized',
            baseline_duration_ms=loop_duration_ms,
            candidate_duration_ms=vector_duration_ms,
            sample_rows=len(vector_results),
        )
        ComputeAccelerationService.record_component_sample(
            component='scenario_simulation',
            duration_ms=vector_duration_ms,
            rows=len(vector_results),
            backend='python_vectorized',
            context=context,
            native_enabled=False,
            native_available=False,
            preferred_backend='python_vectorized',
            metadata={
                'vectorized_duration_ms': round(vector_duration_ms, 3),
                'loop_duration_ms': round(loop_duration_ms, 3),
                'speedup_ratio': round(loop_duration_ms / vector_duration_ms, 3)
                if vector_duration_ms
                else None,
            },
            skip_benchmark_marker=True,
        )
        speedup_ratio = (
            round(loop_duration_ms / vector_duration_ms, 3)
            if vector_duration_ms
            else None
        )
        return {
            'component': 'scenario_simulation',
            'component_label': '批量情景模拟',
            'summary': str(gate_patch.get('benchmark_summary') or ''),
            'artifacts': [
                {
                    'type': 'benchmark_report',
                    'name': '批量情景模拟 benchmark',
                    'uri': f'benchmark://scenario_simulation/{operation_id or "manual"}',
                    'metadata': {
                        'vectorized_duration_ms': round(vector_duration_ms, 3),
                        'loop_duration_ms': round(loop_duration_ms, 3),
                        'speedup_ratio': speedup_ratio,
                    },
                }
            ],
            'metrics': {
                'benchmark_component': 'scenario_simulation',
                'benchmark_backend': 'python_vectorized',
                'vectorized_duration_ms': round(vector_duration_ms, 3),
                'loop_duration_ms': round(loop_duration_ms, 3),
                'speedup_ratio': speedup_ratio,
                'compute_metrics': {
                    'scenario_simulation': {
                        'backend': 'python_vectorized',
                        'duration_ms': round(vector_duration_ms, 3),
                        'input_rows': len(vector_results),
                        'context': context,
                        'native_enabled': False,
                        'native_available': False,
                        'module_name': '',
                        'fallback_reason': '',
                        'rollout_mode': 'benchmark',
                        'rollout_reason': 'vectorized benchmark completed',
                        'benchmark_ready': bool(gate_patch.get('benchmark_passed')),
                        'benchmark_status': str(gate_patch.get('benchmark_status') or ''),
                        'benchmark_summary': str(gate_patch.get('benchmark_summary') or ''),
                        'benchmark_speedup_ratio': gate_patch.get('benchmark_speedup_ratio'),
                    }
                },
            },
            'result': {
                'vectorized_duration_ms': round(vector_duration_ms, 3),
                'loop_duration_ms': round(loop_duration_ms, 3),
                'speedup_ratio': speedup_ratio,
                'scenario_count': len(vector_results),
            },
        }

    @classmethod
    def _sample_frame(cls, rows: int) -> pd.DataFrame:
        rows = max(48, min(rows, 12000))
        hours = pd.date_range('2025-01-01', periods=rows, freq='H')
        base = 140 + 22 * np.sin(np.arange(rows) * 2 * np.pi / 24)
        seasonal = 18 * np.sin(np.arange(rows) * 2 * np.pi / (24 * 7))
        temperature = 23 + 6 * np.sin(np.arange(rows) * 2 * np.pi / 24)
        return pd.DataFrame(
            {
                'Date': hours,
                'Hour': hours.hour,
                'DayOfWeek': hours.dayofweek,
                'Month': hours.month,
                'Temperature': temperature,
                'Price': np.where(
                    (hours.hour >= 18) & (hours.hour < 22),
                    1.0,
                    np.where(hours.hour < 8, 0.3, 0.6),
                ),
                'Site_Load': base
                + seasonal
                + np.random.default_rng(7).normal(0, 3, len(hours)),
            }
        )
