from __future__ import annotations

from unittest.mock import patch


def test_vertex_training_event_endpoint_accepts_internal_callback(client):
    payload = {
        'vertex_state': 'JOB_STATE_RUNNING',
        'phase': 'vertex_training',
        'progress': 42,
        'message': 'Vertex training container running',
    }

    with (
        patch('api.training_runtime._validate_internal_token', return_value=True),
        patch(
            'api.training_runtime.VertexTrainingReconciler.process_callback_event',
            return_value={'job_id': 'op-1', 'status': 'running', 'progress': 42},
        ) as process_callback_event,
    ):
        response = client.post('/internal/training/vertex/op-1/events', json=payload)

    assert response.status_code == 202
    process_callback_event.assert_called_once_with('op-1', payload)


def test_vertex_training_reconcile_endpoint_dispatches_reconciler(client):
    with (
        patch('api.training_runtime._validate_internal_token', return_value=True),
        patch(
            'api.training_runtime.VertexTrainingReconciler.reconcile_operation',
            return_value={'job_id': 'op-1', 'status': 'running', 'progress': 15},
        ) as reconcile_operation,
    ):
        response = client.post('/internal/training/vertex/op-1/reconcile', json={})

    assert response.status_code == 202
    reconcile_operation.assert_called_once()
