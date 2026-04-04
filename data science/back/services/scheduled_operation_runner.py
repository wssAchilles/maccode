"""Execution helpers for scheduler-style operations.

These helpers are shared by cron jobs and manual control-task runs so
scheduled operations do not fork into separate implementations.
"""

from __future__ import annotations

from typing import Any, Dict

from services.external_data_service import ExternalDataService
from services.ml_service import EnergyPredictor


def run_fetch_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    service = ExternalDataService()
    success = service.fetch_and_publish()
    if not success:
        raise RuntimeError('fetch_and_publish returned False')
    runtime_metrics = dict(service.last_runtime_metrics or {})

    return {
        'task_name': str(payload.get('task_name') or 'fetch_data'),
        'success': True,
        'storage_path': 'data/processed/cleaned_energy_data_all.csv',
        'compute_metrics': dict(runtime_metrics.get('compute_metrics') or {}),
        'metrics': runtime_metrics,
        'artifacts': [
            {
                'type': 'dataset',
                'name': 'Processed energy dataset',
                'uri': 'data/processed/cleaned_energy_data_all.csv',
                'metadata': {'source': 'scheduled-fetch'},
            }
        ],
    }


def run_train_model(payload: Dict[str, Any]) -> Dict[str, Any]:
    predictor = EnergyPredictor()
    n_estimators = int(payload.get('n_estimators', 100) or 100)
    use_firebase_storage = bool(payload.get('use_firebase_storage', True))
    metrics = predictor.train_model(
        use_firebase_storage=use_firebase_storage,
        n_estimators=n_estimators,
    )
    operation_metrics = {
        'model_type': metrics.get('model_type'),
        'train_rmse': metrics.get('train_rmse'),
        'test_rmse': metrics.get('test_rmse'),
        'r2_score': metrics.get('r2_score'),
        'compute_metrics': dict(predictor.last_compute_metrics or {}),
    }

    return {
        **metrics,
        'task_name': str(payload.get('task_name') or 'train_model'),
        'model_path': predictor.firebase_model_path,
        'compute_metrics': dict(predictor.last_compute_metrics or {}),
        'metrics': operation_metrics,
        'artifacts': [
            {
                'type': 'model',
                'name': 'Daily forecast model',
                'uri': predictor.firebase_model_path,
                'metadata': {'model_type': metrics.get('model_type')},
            }
        ],
    }
