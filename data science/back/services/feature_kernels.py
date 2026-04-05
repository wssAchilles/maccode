"""Hot-path feature kernels with optional native acceleration."""

from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

from services.compute_backend_selector import select_feature_engineering_backend
from services.compute_native_loader import load_native_module


def _python_load_features(site_load: pd.Series) -> Dict[str, pd.Series]:
    shifted = site_load.shift(1)
    rolling6 = shifted.rolling(window=6)
    rolling24 = shifted.rolling(window=24)
    rolling_mean_24h = rolling24.mean()
    rolling_std_24h = rolling24.std()

    return {
        'Lag_1h': site_load.shift(1),
        'Lag_24h': site_load.shift(24),
        'Lag_168h': site_load.shift(168),
        'Rolling_Mean_6h': rolling6.mean(),
        'Rolling_Std_6h': rolling6.std(),
        'Rolling_Mean_24h': rolling_mean_24h,
        'Quantile_95_24h': rolling24.quantile(0.95),
        'Quantile_05_24h': rolling24.quantile(0.05),
        'Volatility_24h': rolling_std_24h / rolling_mean_24h.replace(0, np.nan),
        'Load_Change_1h': site_load.diff(),
        'Load_Change_Pct_1h': site_load.pct_change() * 100,
    }


def _native_load_features(site_load: pd.Series) -> Dict[str, pd.Series]:
    module = load_native_module()
    if module is None:
        raise RuntimeError('native rolling feature module is unavailable')

    payload = module.compute_load_features(site_load.astype(float).tolist())
    return {
        key: pd.Series(payload[key], index=site_load.index, dtype='float64')
        for key in (
            'Lag_1h',
            'Lag_24h',
            'Lag_168h',
            'Rolling_Mean_6h',
            'Rolling_Std_6h',
            'Rolling_Mean_24h',
            'Quantile_95_24h',
            'Quantile_05_24h',
            'Volatility_24h',
            'Load_Change_1h',
            'Load_Change_Pct_1h',
        )
    }


def compute_load_features(
    site_load: pd.Series,
    *,
    context: str = '',
) -> Tuple[Dict[str, pd.Series], Dict[str, Any]]:
    """Compute lag and rolling features via the configured backend."""

    selection = select_feature_engineering_backend(context=context)
    backend = selection['backend']

    if selection['backend'] == 'native_cpp':
        try:
            return _native_load_features(site_load), {
                'backend': 'native_cpp',
                'native_enabled': selection['native_enabled'],
                'native_available': selection['native_available'],
                'module_name': selection['module_name'],
                'fallback_reason': '',
                'rollout_mode': selection['rollout_mode'],
                'rollout_reason': selection['rollout_reason'],
                'canary_percent': selection['canary_percent'],
                'benchmark_ready': selection['benchmark_ready'],
                'benchmark_status': selection.get('benchmark_status') or '',
                'benchmark_summary': selection.get('benchmark_summary') or '',
            }
        except Exception as exc:
            backend = 'python_pandas'
            fallback_reason = str(exc)
        else:
            fallback_reason = ''
    else:
        fallback_reason = selection['rollout_reason']

    return _python_load_features(site_load), {
        'backend': backend,
        'native_enabled': selection['native_enabled'],
        'native_available': selection['native_available'],
        'module_name': selection['module_name'],
        'fallback_reason': fallback_reason,
        'rollout_mode': selection['rollout_mode'],
        'rollout_reason': selection['rollout_reason'],
        'canary_percent': selection['canary_percent'],
        'benchmark_ready': selection['benchmark_ready'],
        'benchmark_status': selection.get('benchmark_status') or '',
        'benchmark_summary': selection.get('benchmark_summary') or '',
    }
