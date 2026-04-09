"""Tests for cron-triggered scheduler dispatch behavior."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

BACK_ROOT = Path(__file__).resolve().parents[1]
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

from scheduler import DataPipelineScheduler


class SchedulerDispatchTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TASKS_EXECUTION_MODE'] = 'inline'

    def test_fetch_data_job_dispatches_via_operation_dispatcher(self):
        scheduler = DataPipelineScheduler(app=self.app)
        operation = {'job_id': 'fetch-op-1', 'type': 'fetch_data', 'status': 'queued'}

        with patch(
            'scheduler.ControlTaskService.ensure_control_task',
            return_value={'id': 'fetch_data_hourly'},
        ), patch(
            'scheduler.OperationService.create_operation',
            return_value=operation,
        ), patch(
            'scheduler.OperationService.dispatch_operation',
        ) as dispatch_operation, patch(
            'scheduler.OperationService.execute_operation',
        ) as execute_operation:
            result = scheduler.fetch_data_job()

        dispatch_operation.assert_called_once_with(self.app, 'fetch-op-1', 'fetch_data')
        execute_operation.assert_not_called()
        self.assertEqual(result, operation)

    def test_train_model_job_dispatches_via_operation_dispatcher(self):
        scheduler = DataPipelineScheduler(app=self.app)
        operation = {'job_id': 'train-op-1', 'type': 'train_model', 'status': 'queued'}

        with patch(
            'scheduler.ControlTaskService.ensure_control_task',
            return_value={'id': 'train_model_daily'},
        ), patch(
            'scheduler.OperationService.create_operation',
            return_value=operation,
        ), patch(
            'scheduler.OperationService.dispatch_operation',
        ) as dispatch_operation, patch(
            'scheduler.OperationService.execute_operation',
        ) as execute_operation:
            result = scheduler.train_model_job()

        dispatch_operation.assert_called_once_with(self.app, 'train-op-1', 'train_model')
        execute_operation.assert_not_called()
        self.assertEqual(result, operation)

    def test_scheduler_falls_back_to_inline_process_dispatch_without_app(self):
        scheduler = DataPipelineScheduler()
        operation = {'job_id': 'fetch-op-2', 'type': 'fetch_data', 'status': 'queued'}

        with patch(
            'scheduler.ControlTaskService.ensure_control_task',
            return_value={'id': 'fetch_data_hourly'},
        ), patch(
            'scheduler.OperationService.create_operation',
            return_value=operation,
        ), patch(
            'scheduler.OperationService.process_dispatch',
        ) as process_dispatch, patch(
            'scheduler.OperationService.dispatch_operation',
        ) as dispatch_operation:
            result = scheduler.fetch_data_job()

        process_dispatch.assert_called_once_with('fetch-op-2')
        dispatch_operation.assert_not_called()
        self.assertEqual(result, operation)


if __name__ == '__main__':
    unittest.main()
