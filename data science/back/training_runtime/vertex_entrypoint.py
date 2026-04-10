"""Entrypoint executed inside Vertex AI custom training containers."""

from __future__ import annotations

import os
import traceback
import uuid
from typing import Any, Dict, Optional

import requests

from services.deep_learning_runtime_service import execute_deep_learning_training


class VertexCallbackClient:
    def __init__(self) -> None:
        self.base_url = str(os.getenv('TRAINING_CALLBACK_BASE_URL') or '').rstrip('/')
        self.token = str(os.getenv('TRAINING_CALLBACK_TOKEN') or '')
        self.operation_id = str(os.getenv('TRAINING_OPERATION_ID') or '')
        self.vertex_state = 'JOB_STATE_RUNNING'

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.token and self.operation_id)

    def send(
        self,
        *,
        phase: str,
        progress: int,
        message: str,
        metrics: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        artifacts: Optional[list[Dict[str, Any]]] = None,
        error: Optional[Dict[str, Any]] = None,
        vertex_state: Optional[str] = None,
    ) -> None:
        if not self.enabled:
            return
        url = f'{self.base_url}/internal/training/vertex/{self.operation_id}/events'
        payload = {
            'event_id': str(uuid.uuid4()),
            'vertex_job_name': os.getenv('CLOUD_ML_JOB_ID') or '',
            'vertex_state': vertex_state or self.vertex_state,
            'phase': phase,
            'progress': progress,
            'message': message,
            'metrics': metrics or {},
            'result': result,
            'artifacts': artifacts or [],
            'error': error,
            'timestamp': None,
        }
        response = requests.post(
            url,
            json=payload,
            headers={'X-Internal-Job-Token': self.token},
            timeout=30,
        )
        response.raise_for_status()


def main() -> None:
    uid = str(os.getenv('TRAINING_UID') or '').strip()
    operation_id = str(os.getenv('TRAINING_OPERATION_ID') or '').strip()
    payload = {
        'storage_path': os.getenv('TRAINING_STORAGE_PATH'),
        'model_type': os.getenv('TRAINING_MODEL_TYPE', 'lstm'),
        'target_column': os.getenv('TRAINING_TARGET_COLUMN'),
        'window_size': int(os.getenv('TRAINING_WINDOW_SIZE', '24')),
        'horizon': int(os.getenv('TRAINING_HORIZON', '1')),
        'epochs': int(os.getenv('TRAINING_EPOCHS', '10')),
        'batch_size': int(os.getenv('TRAINING_BATCH_SIZE', '32')),
    }
    callback = VertexCallbackClient()
    callback.send(
        phase='vertex_training',
        progress=20,
        message='Vertex training container started',
    )
    try:
        result = execute_deep_learning_training(
            uid,
            payload,
            run_id=operation_id,
            progress_callback=lambda progress, message, phase, metrics=None: callback.send(
                phase=phase,
                progress=progress,
                message=message,
                metrics=metrics,
            ),
        )
        callback.send(
            phase='completed',
            progress=100,
            message='Vertex training completed',
            metrics=result.get('metrics') if isinstance(result, dict) else {},
            result=result,
            artifacts=result.get('artifacts') if isinstance(result, dict) else [],
            vertex_state='JOB_STATE_SUCCEEDED',
        )
    except Exception as exc:
        callback.send(
            phase='failed',
            progress=100,
            message=f'Vertex training failed: {exc}',
            error={
                'message': str(exc),
                'traceback': traceback.format_exc(),
            },
            vertex_state='JOB_STATE_FAILED',
        )
        raise


if __name__ == '__main__':
    main()
