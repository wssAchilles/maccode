#!/usr/bin/env python3
"""Run a lightweight benchmark for the compute acceleration layer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACK_DIR = ROOT_DIR / 'back'
if str(BACK_DIR) not in sys.path:
    sys.path.insert(0, str(BACK_DIR))

from services.compute_benchmark_service import ComputeBenchmarkService
from services.compute_acceleration_service import ComputeAccelerationService


def main() -> int:
    ComputeBenchmarkService.run({'component': 'feature_engineering'}, operation_id='script')
    ComputeBenchmarkService.run({'component': 'scenario_simulation'}, operation_id='script')

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
