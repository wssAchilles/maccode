"""Structured advanced feature engineering with profiling and backend fallback."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from services.compute_acceleration_service import ComputeAccelerationService
from services.compute_rollout_guard_service import ComputeRolloutGuardService
from services.feature_kernels import compute_load_features


class FeatureEngineeringService:
    """Build advanced load features without bloating the data processor class."""

    @staticmethod
    def build_advanced_features(
        df: pd.DataFrame,
        *,
        dropna: bool = True,
        use_enhanced: bool = True,
        context: str = 'feature_pipeline',
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        started_at = perf_counter()
        working_df = df.sort_values('Date').reset_index(drop=True).copy()
        load_features, kernel_meta = compute_load_features(
            working_df['Site_Load'],
            context=context,
        )

        for column, series in load_features.items():
            working_df[column] = series

        working_df['Price_Change'] = working_df['Price'].diff().abs()
        working_df['Temp_x_Hour'] = working_df['Temperature'] * working_df['Hour']
        working_df['Lag24_x_DayOfWeek'] = working_df['Lag_24h'] * working_df['DayOfWeek']

        enhanced_features_added: List[str] = []
        if use_enhanced and 'Season' in working_df.columns:
            working_df['Temp_x_Season'] = working_df['Temperature'] * working_df['Season']
            enhanced_features_added.append('Temp*Season')

            if 'IsWeekend' in working_df.columns:
                working_df['Lag24_x_IsWeekend'] = working_df['Lag_24h'] * working_df['IsWeekend']
                enhanced_features_added.append('Lag24*IsWeekend')

            if 'IsHoliday' in working_df.columns:
                working_df['Hour_x_IsHoliday'] = working_df['Hour'] * working_df['IsHoliday']
                enhanced_features_added.append('Hour*IsHoliday')

            working_df['Month_Sin'] = np.sin(2 * np.pi * working_df['Month'] / 12)
            working_df['Month_Cos'] = np.cos(2 * np.pi * working_df['Month'] / 12)
            working_df['Hour_Sin'] = np.sin(2 * np.pi * working_df['Hour'] / 24)
            working_df['Hour_Cos'] = np.cos(2 * np.pi * working_df['Hour'] / 24)
            enhanced_features_added.extend(['Month_Sin', 'Month_Cos', 'Hour_Sin', 'Hour_Cos'])

        original_len = len(working_df)
        if dropna:
            working_df = working_df.dropna().reset_index(drop=True)
        dropped_len = original_len - len(working_df)

        duration_ms = (perf_counter() - started_at) * 1000.0
        guard_context = f'{context}:feature_engineering'
        guard_state: Dict[str, Any] = {}
        native_modes = {'native_candidate', 'native_enforced'}
        if kernel_meta['backend'] == 'native_cpp':
            guard_state = ComputeRolloutGuardService.record_native_success(
                'feature_engineering',
                context=guard_context,
            )
        elif (
            str(kernel_meta.get('rollout_mode') or '') in native_modes
            and str(kernel_meta.get('fallback_reason') or '').strip()
        ):
            guard_state = ComputeRolloutGuardService.record_native_failure(
                'feature_engineering',
                reason=str(kernel_meta.get('fallback_reason') or ''),
                context=guard_context,
                rollout_mode=str(kernel_meta.get('rollout_mode') or ''),
            )

        component_guard = (
            dict(guard_state.get('component_state') or {})
            if isinstance(guard_state, dict)
            else {}
        )
        auto_rollback = (
            dict(guard_state.get('auto_rollback') or {})
            if isinstance(guard_state, dict) and isinstance(guard_state.get('auto_rollback'), dict)
            else {}
        )
        metrics = {
            'backend': kernel_meta['backend'],
            'native_enabled': kernel_meta['native_enabled'],
            'native_available': kernel_meta['native_available'],
            'module_name': kernel_meta['module_name'],
            'fallback_reason': kernel_meta.get('fallback_reason') or '',
            'rollout_mode': kernel_meta.get('rollout_mode') or '',
            'rollout_reason': kernel_meta.get('rollout_reason') or '',
            'canary_percent': int(kernel_meta.get('canary_percent') or 0),
            'benchmark_ready': bool(kernel_meta.get('benchmark_ready')),
            'benchmark_status': str(kernel_meta.get('benchmark_status') or ''),
            'benchmark_summary': str(kernel_meta.get('benchmark_summary') or ''),
            'duration_ms': round(duration_ms, 3),
            'input_rows': original_len,
            'output_rows': len(working_df),
            'dropped_rows': dropped_len,
            'enhanced_features_added': enhanced_features_added,
            'context': context,
            'guard_recent_failure_count': int(
                component_guard.get('recent_failure_count') or 0,
            ),
            'guard_last_failure_at': str(component_guard.get('last_failure_at') or ''),
            'guard_last_failure_reason': str(
                component_guard.get('last_failure_reason') or '',
            ),
            'guard_last_auto_rollback_at': str(
                component_guard.get('last_auto_rollback_at') or '',
            ),
            'guard_last_auto_rollback_reason': str(
                component_guard.get('last_auto_rollback_reason') or '',
            ),
            'guard_auto_rollback_applied': bool(auto_rollback),
            'guard_failure_threshold': int(guard_state.get('failure_threshold') or 0)
            if isinstance(guard_state, dict)
            else 0,
            'guard_window_minutes': int(guard_state.get('window_minutes') or 0)
            if isinstance(guard_state, dict)
            else 0,
        }

        ComputeAccelerationService.record_component_sample(
            component='feature_engineering',
            duration_ms=duration_ms,
            rows=original_len,
            backend=kernel_meta['backend'],
            context=context,
            native_enabled=kernel_meta['native_enabled'],
            native_available=kernel_meta['native_available'],
            preferred_backend='native_cpp' if kernel_meta['native_enabled'] else 'python_pandas',
            metadata={
                'dropna': dropna,
                'use_enhanced': use_enhanced,
                'output_rows': len(working_df),
                'dropped_rows': dropped_len,
                'fallback_reason': kernel_meta.get('fallback_reason') or '',
                'rollout_mode': kernel_meta.get('rollout_mode') or '',
                'rollout_reason': kernel_meta.get('rollout_reason') or '',
                'benchmark_ready': bool(kernel_meta.get('benchmark_ready')),
                'benchmark_status': str(kernel_meta.get('benchmark_status') or ''),
                'benchmark_summary': str(kernel_meta.get('benchmark_summary') or ''),
                'guard_recent_failure_count': int(
                    component_guard.get('recent_failure_count') or 0,
                ),
                'guard_last_auto_rollback_at': str(
                    component_guard.get('last_auto_rollback_at') or '',
                ),
                'guard_last_auto_rollback_reason': str(
                    component_guard.get('last_auto_rollback_reason') or '',
                ),
                'guard_auto_rollback_applied': bool(auto_rollback),
            },
        )

        return working_df, metrics
