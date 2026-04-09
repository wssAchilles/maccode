from __future__ import annotations

from unittest.mock import patch


def test_operation_stream_prefers_orchestrator_proxy(client, auth_headers):
    with (
        patch(
            'services.firebase_service.FirebaseService.verify_token',
            return_value={'uid': 'test-user'},
        ),
        patch(
            'api.operations.OperationService.get_operation',
            return_value={'job_id': 'op-1', 'status': 'running'},
        ),
        patch(
            'api.operations._proxy_stream_from_orchestrator',
            return_value=iter(
                [
                    b'event: snapshot\n',
                    b'data: {"frame_type":"snapshot","payload":{"job_id":"op-1"}}\n\n',
                ]
            ),
        ),
    ):
        response = client.get('/api/operations/op-1/stream', headers=auth_headers)

    assert response.status_code == 200
    assert response.mimetype == 'text/event-stream'
    assert b'event: snapshot' in response.data


def test_operation_stream_falls_back_to_local_generator(client, auth_headers):
    with (
        patch(
            'services.firebase_service.FirebaseService.verify_token',
            return_value={'uid': 'test-user'},
        ),
        patch(
            'api.operations.OperationService.get_operation',
            return_value={'job_id': 'op-1', 'status': 'running'},
        ),
        patch('api.operations._proxy_stream_from_orchestrator', return_value=None),
        patch(
            'api.operations.stream_operation_events',
            return_value=iter(
                [
                    'event: operation.snapshot\n',
                    'data: {"job_id":"op-1"}\n\n',
                ]
            ),
        ),
    ):
        response = client.get('/api/operations/op-1/stream', headers=auth_headers)

    assert response.status_code == 200
    assert response.mimetype == 'text/event-stream'
    assert b'event: operation.snapshot' in response.data
