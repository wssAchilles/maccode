from __future__ import annotations

from unittest.mock import patch


def test_internal_dispatch_runs_heavy_worker_inline(client):
    with (
        patch('api.operations._validate_internal_token', return_value=True),
        patch(
            'api.operations.OperationService.get_operation_for_execution',
            return_value={'job_id': 'op-1', 'execution_target': 'heavy_worker'},
        ),
        patch('api.operations.OperationService.process_dispatch') as process_dispatch,
        patch('api.operations.start_internal_operation_dispatch') as start_dispatch,
    ):
        response = client.post('/internal/operations/op-1/dispatch')

    assert response.status_code == 202
    process_dispatch.assert_called_once_with('op-1')
    start_dispatch.assert_not_called()


def test_internal_dispatch_keeps_background_runtime_for_light_worker(client):
    with (
        patch('api.operations._validate_internal_token', return_value=True),
        patch(
            'api.operations.OperationService.get_operation_for_execution',
            return_value={'job_id': 'op-2', 'execution_target': 'light_worker'},
        ),
        patch(
            'api.operations.start_internal_operation_dispatch',
            return_value={'operation_id': 'op-2', 'status': 'accepted', 'dispatch_mode': 'background'},
        ) as start_dispatch,
        patch('api.operations.OperationService.process_dispatch') as process_dispatch,
    ):
        response = client.post('/internal/operations/op-2/dispatch')

    assert response.status_code == 202
    process_dispatch.assert_not_called()
    start_dispatch.assert_called_once()
