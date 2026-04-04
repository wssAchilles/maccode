#!/usr/bin/env python3
"""Run a lightweight benchmark for the compute acceleration layer."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
BACK_DIR = ROOT_DIR / 'back'
if str(BACK_DIR) not in sys.path:
    sys.path.insert(0, str(BACK_DIR))

from services.compute_acceleration_service import ComputeAccelerationService
from services.data_processor import EnergyDataProcessor
from services.optimization_service import EnergyOptimizer


def _load_sample_frame() -> pd.DataFrame:
    candidates = (
        ROOT_DIR / 'data' / 'processed' / 'cleaned_energy_data_all.csv',
        BACK_DIR / 'data' / 'processed' / 'cleaned_energy_data_all.csv',
    )
    for candidate in candidates:
        if candidate.exists():
            return pd.read_csv(candidate, parse_dates=['Date']).tail(5000).reset_index(drop=True)

    hours = pd.date_range('2025-01-01', periods=5000, freq='H')
    base = 140 + 22 * np.sin(np.arange(5000) * 2 * np.pi / 24)
    seasonal = 18 * np.sin(np.arange(5000) * 2 * np.pi / (24 * 7))
    temperature = 23 + 6 * np.sin(np.arange(5000) * 2 * np.pi / 24)
    return pd.DataFrame(
        {
            'Date': hours,
            'Hour': hours.hour,
            'DayOfWeek': hours.dayofweek,
            'Temperature': temperature,
            'Price': np.where((hours.hour >= 18) & (hours.hour < 22), 1.0, np.where(hours.hour < 8, 0.3, 0.6)),
            'Site_Load': base + seasonal + np.random.default_rng(7).normal(0, 3, len(hours)),
        }
    )


def main() -> int:
    frame = _load_sample_frame()
    processor = EnergyDataProcessor()
    frame = processor.add_enhanced_time_features(frame)
    profiled = processor.add_advanced_features(
        frame,
        dropna=False,
        use_enhanced=True,
        compute_context='benchmark_feature_engineering',
    )

    optimizer = EnergyOptimizer()
    optimizer.simulate_scenarios(
        load_profile=profiled['Site_Load'].tail(24).astype(float).tolist(),
        price_profile=profiled['Price'].tail(24).astype(float).tolist(),
        variations={
            'battery_capacity': [50, 100, 150],
            'max_power': [20, 40, 60],
        },
        profile_context='benchmark_scenario_simulation',
    )

    snapshot = ComputeAccelerationService.get_status()
    output_dir = ROOT_DIR / 'outputs'
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = output_dir / 'compute_acceleration_snapshot.json'
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(f'\nSnapshot written to: {snapshot_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
