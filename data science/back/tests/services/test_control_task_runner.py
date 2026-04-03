"""Tests for bridging control tasks into operations."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

BACK_ROOT = Path(__file__).resolve().parents[2]
if str(BACK_ROOT) not in sys.path:
    sys.path.insert(0, str(BACK_ROOT))

SERVER_TIMESTAMP = object()


class _FailedPrecondition(Exception):
    pass


google_module = types.ModuleType('google')
api_core_module = types.ModuleType('google.api_core')
exceptions_module = types.ModuleType('google.api_core.exceptions')
exceptions_module.FailedPrecondition = _FailedPrecondition
cloud_module = types.ModuleType('google.cloud')
firestore_module = types.ModuleType('google.cloud.firestore')
firestore_v1_module = types.ModuleType('google.cloud.firestore_v1')


class _FirestoreQuery:
    DESCENDING = 'DESCENDING'


class _FirestoreClient:
    def __init__(self, *args, **kwargs):
        pass


firestore_module.Query = _FirestoreQuery
firestore_module.Client = _FirestoreClient
firestore_v1_module.SERVER_TIMESTAMP = SERVER_TIMESTAMP

google_module.api_core = api_core_module
google_module.cloud = cloud_module
api_core_module.exceptions = exceptions_module
cloud_module.firestore = firestore_module
cloud_module.firestore_v1 = firestore_v1_module

sys.modules.setdefault('google', google_module)
sys.modules.setdefault('google.api_core', api_core_module)
sys.modules.setdefault('google.api_core.exceptions', exceptions_module)
sys.modules.setdefault('google.cloud', cloud_module)
sys.modules.setdefault('google.cloud.firestore', firestore_module)
sys.modules.setdefault('google.cloud.firestore_v1', firestore_v1_module)

history_service_module = types.ModuleType('services.history_service')


class _HistoryServiceStub:
    @staticmethod
    def add_history(**kwargs):
        return 'history-1'


history_service_module.HistoryService = _HistoryServiceStub
sys.modules.setdefault('services.history_service', history_service_module)

job_workflows_module = types.ModuleType('services.job_workflows')
job_workflows_module.run_analysis_workflow = lambda *args, **kwargs: {}
job_workflows_module.run_deep_learning_workflow = lambda *args, **kwargs: {}
job_workflows_module.run_optimization_workflow = lambda *args, **kwargs: {}
job_workflows_module.run_rag_ingest_workflow = lambda *args, **kwargs: {}
sys.modules.setdefault('services.job_workflows', job_workflows_module)

from services.control_task_runner import (
    ControlTaskConfigurationError,
    ControlTaskDisabledError,
    ControlTaskNotFoundError,
    run_control_task,
)


class ControlTaskRunnerTestCase(unittest.TestCase):
    def test_run_control_task_creates_operation_from_definition(self):
        with patch(
            'services.control_task_runner.ControlTaskService.get_control_task',
            return_value={
                'id': 'train_model_daily',
                'enabled': True,
                'kind': 'scheduler',
                'operation_type': 'train_model',
                'default_input': {'task_name': 'train_model', 'n_estimators': 100},
                'approval_policy': {'required': False, 'mode': 'auto'},
            },
        ), patch(
            'services.control_task_runner.OperationService.create_operation',
            return_value={'job_id': 'op-1', 'type': 'train_model', 'status': 'queued'},
        ) as create_operation:
            operation = run_control_task(
                uid='user-1',
                control_task_id='train_model_daily',
                input_overrides={'n_estimators': 200},
                trigger='manual',
            )

        self.assertEqual(operation['job_id'], 'op-1')
        create_operation.assert_called_once()
        args, kwargs = create_operation.call_args
        self.assertEqual(args[0], 'user-1')
        self.assertEqual(args[1], 'train_model')
        self.assertEqual(args[2]['n_estimators'], 200)
        self.assertEqual(kwargs['control_task_id'], 'train_model_daily')
        self.assertEqual(kwargs['trigger'], 'manual')

    def test_run_control_task_rejects_missing_definition(self):
        with patch(
            'services.control_task_runner.ControlTaskService.get_control_task',
            return_value=None,
        ):
            with self.assertRaises(ControlTaskNotFoundError):
                run_control_task(uid='user-1', control_task_id='missing')

    def test_run_control_task_rejects_disabled_definition(self):
        with patch(
            'services.control_task_runner.ControlTaskService.get_control_task',
            return_value={'id': 'paused_task', 'enabled': False},
        ):
            with self.assertRaises(ControlTaskDisabledError):
                run_control_task(uid='user-1', control_task_id='paused_task')

    def test_run_control_task_requires_operation_type(self):
        with patch(
            'services.control_task_runner.ControlTaskService.get_control_task',
            return_value={
                'id': 'broken_task',
                'enabled': True,
                'default_input': {},
            },
        ):
            with self.assertRaises(ControlTaskConfigurationError):
                run_control_task(uid='user-1', control_task_id='broken_task')


if __name__ == '__main__':
    unittest.main()
