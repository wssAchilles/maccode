"""Execution helpers for scheduler-style operations.

These helpers are shared by cron jobs and manual control-task runs so
scheduled operations do not fork into separate implementations.
"""

from __future__ import annotations

from typing import Any, Dict

from services.external_data_service import ExternalDataService
from services.ml_service import EnergyPredictor


def run_fetch_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    success = ExternalDataService().fetch_and_publish()
    if not success:
        raise RuntimeError('fetch_and_publish returned False')

    return {
        'task_name': str(payload.get('task_name') or 'fetch_data'),
        'success': True,
        'storage_path': 'data/processed/cleaned_energy_data_all.csv',
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

    return {
        **metrics,
        'task_name': str(payload.get('task_name') or 'train_model'),
        'model_path': predictor.firebase_model_path,
        'artifacts': [
            {
                'type': 'model',
                'name': 'Daily forecast model',
                'uri': predictor.firebase_model_path,
                'metadata': {'model_type': metrics.get('model_type')},
            }
        ],
    }
