from __future__ import annotations

from unittest.mock import patch

from services.runtime_snapshot_service import RuntimeSnapshotService


def test_runtime_snapshot_prefers_rust_control_plane_projection():
    local_tasks = [
        {
            'id': 'train_model_daily',
            'title': '本地每日训练',
            'dependency_state': 'ready',
        }
    ]
    projected_tasks = [
        {
            'id': 'train_model_daily',
            'title': 'Rust 控制面每日训练',
            'dependency_state': 'ready',
            'control_plane_projection': {
                'runtime_state': 'in_flight',
                'in_flight_lock': True,
            },
        },
        {
            'id': 'dataset_ready',
            'title': '数据准备',
            'dependency_state': 'ready',
            'control_plane_projection': {
                'runtime_state': 'scheduled',
                'in_flight_lock': False,
            },
        },
    ]
    projection_payload = {
        'control_plane': {
            'policy_version': 'delta5-connector-lifecycle-v1',
            'degraded': False,
            'connectors': [
                {
                    'connector_name': 'python_worker',
                    'state': 'healthy',
                    'available_capabilities': ['operations.dispatch'],
                    'unavailable_capabilities': [],
                }
            ],
            'degraded_mode': None,
        },
        'control_tasks': {
            'items': projected_tasks,
            'count': 2,
        },
        'degraded_sections': [
            {
                'section': 'control_plane',
                'message': 'Control-plane degraded: python_worker',
            }
        ],
    }

    with (
        patch(
            'services.runtime_snapshot_service.DashboardService.build_summary',
            return_value={'status': 'ok'},
        ),
        patch(
            'services.runtime_snapshot_service.JobService.list_jobs',
            return_value=[],
        ),
        patch(
            'services.runtime_snapshot_service.ControlTaskService.list_control_tasks',
            return_value=local_tasks,
        ),
        patch(
            'services.runtime_snapshot_service.OrchestratorRuntimeProjectionService.get_snapshot',
            return_value=projection_payload,
        ),
        patch(
            'services.runtime_snapshot_service.ComputeGovernanceStatusService.get_policy_view',
            return_value={},
        ),
        patch(
            'services.runtime_snapshot_service.ComputeGovernanceActivityService.list_recent_activity',
            return_value=[],
        ),
    ):
        snapshot = RuntimeSnapshotService.build_shell_snapshot('test-user')

    assert snapshot['projection_version'] == 'shell-runtime-v2'
    assert snapshot['control_plane']['policy_version'] == 'delta5-connector-lifecycle-v1'
    assert snapshot['control_plane']['connectors'][0]['connector_name'] == 'python_worker'
    assert snapshot['control_plane']['degraded_mode'] is None
    assert snapshot['control_tasks']['count'] == 2
    assert snapshot['control_tasks']['items'][0]['title'] == 'Rust 控制面每日训练'
    assert snapshot['control_tasks']['items'][0]['control_plane_projection']['in_flight_lock'] is True
    assert snapshot['control_tasks']['items'][1]['id'] == 'dataset_ready'
    assert snapshot['degraded_sections'][-1]['section'] == 'control_plane'


def test_runtime_snapshot_falls_back_to_local_control_tasks_when_projection_unavailable():
    local_tasks = [
        {
            'id': 'train_model_daily',
            'title': '本地每日训练',
            'dependency_state': 'ready',
        }
    ]

    with (
        patch(
            'services.runtime_snapshot_service.DashboardService.build_summary',
            return_value={'status': 'ok'},
        ),
        patch(
            'services.runtime_snapshot_service.JobService.list_jobs',
            return_value=[],
        ),
        patch(
            'services.runtime_snapshot_service.ControlTaskService.list_control_tasks',
            return_value=local_tasks,
        ),
        patch(
            'services.runtime_snapshot_service.OrchestratorRuntimeProjectionService.get_snapshot',
            side_effect=RuntimeError('orchestrator timeout'),
        ),
        patch(
            'services.runtime_snapshot_service.ComputeGovernanceStatusService.get_policy_view',
            return_value={},
        ),
        patch(
            'services.runtime_snapshot_service.ComputeGovernanceActivityService.list_recent_activity',
            return_value=[],
        ),
    ):
        snapshot = RuntimeSnapshotService.build_shell_snapshot('test-user')

    assert snapshot['projection_version'] == 'shell-runtime-v2'
    assert snapshot['control_tasks']['count'] == 1
    assert snapshot['control_tasks']['items'][0]['title'] == '本地每日训练'
    assert snapshot['control_plane'] == {}
    assert any(
        item['section'] == 'control_plane_projection'
        and 'orchestrator timeout' in item['message']
        for item in snapshot['degraded_sections']
    )
