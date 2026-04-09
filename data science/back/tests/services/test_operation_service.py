"""Tests for the unified operation service."""

from __future__ import annotations

import copy
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
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
firestore_module.transactional = lambda fn: fn
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
    def _as_iso(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: _HistoryServiceStub._as_iso(item) for key, item in value.items()}
        if isinstance(value, list):
            return [_HistoryServiceStub._as_iso(item) for item in value]
        return value

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

from services import operation_service as operation_service_module
from services.operation_service import OperationService

operation_service_module.firestore.transactional = lambda fn: fn

firestore = firestore_module


def _replace_server_timestamps(value):
    if value is SERVER_TIMESTAMP:
        return datetime.now(timezone.utc)
    if isinstance(value, dict):
        return {key: _replace_server_timestamps(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_server_timestamps(item) for item in value]
    return copy.deepcopy(value)


class _FakeSnapshot:
    def __init__(self, doc_id: str, data=None, exists: bool = False):
        self.id = doc_id
        self._data = copy.deepcopy(data) if data is not None else None
        self.exists = exists

    def to_dict(self):
        return copy.deepcopy(self._data) if self._data is not None else None


class _FakeQuery:
    def __init__(self, collection, items=None):
        self._collection = collection
        self._items = list(items) if items is not None else collection._items()

    def where(self, field: str, op: str, value):
        if op != '==':
            raise NotImplementedError(f'Unsupported operator: {op}')
        return _FakeQuery(
            self._collection,
            [(doc_id, data) for doc_id, data in self._items if data.get(field) == value],
        )

    def order_by(self, field: str, direction=None):
        reverse = direction == firestore.Query.DESCENDING
        return _FakeQuery(
            self._collection,
            sorted(
                self._items,
                key=lambda item: item[1].get(field) or datetime.min.replace(tzinfo=timezone.utc),
                reverse=reverse,
            ),
        )

    def limit(self, count: int):
        return _FakeQuery(self._collection, self._items[:count])

    def stream(self):
        return [_FakeSnapshot(doc_id, data, exists=True) for doc_id, data in self._items]


class _FakeDocumentReference:
    def __init__(self, collection, doc_id: str):
        self._collection = collection
        self.id = doc_id

    def get(self, transaction=None):
        data = self._collection._docs.get(self.id)
        return _FakeSnapshot(self.id, data, exists=data is not None)

    def set(self, payload, merge: bool = False):
        normalized = _replace_server_timestamps(payload)
        if merge and self.id in self._collection._docs:
            current = copy.deepcopy(self._collection._docs[self.id])
            current.update(normalized)
            self._collection._docs[self.id] = current
        else:
            self._collection._docs[self.id] = copy.deepcopy(normalized)

    def collection(self, name: str):
        return self._collection._subcollection(self.id, name)


class _FakeCollection:
    def __init__(self):
        self._docs = {}
        self._subcollections = {}
        self._counter = 0

    def _items(self):
        return list(self._docs.items())

    def _subcollection(self, doc_id: str, name: str):
        doc_subcollections = self._subcollections.setdefault(doc_id, {})
        if name not in doc_subcollections:
            doc_subcollections[name] = _FakeCollection()
        return doc_subcollections[name]

    def document(self, doc_id: str | None = None):
        if doc_id is None:
            self._counter += 1
            doc_id = f'auto-{self._counter}'
        return _FakeDocumentReference(self, doc_id)

    def where(self, field: str, op: str, value):
        return _FakeQuery(self).where(field, op, value)

    def order_by(self, field: str, direction=None):
        return _FakeQuery(self).order_by(field, direction=direction)

    def limit(self, count: int):
        return _FakeQuery(self).limit(count)

    def stream(self):
        return _FakeQuery(self).stream()


class _FakeFirestoreClientInstance:
    def __init__(self, operations, control_tasks):
        self._collections = {
            'jobs': operations,
            'control_tasks': control_tasks,
        }

    def collection(self, name: str):
        return self._collections[name]

    def transaction(self):
        return _FakeTransaction()


class _FakeTransaction:
    def set(self, document, payload, merge: bool = False):
        document.set(payload, merge=merge)


class TestOperationService(OperationService):
    _operations = _FakeCollection()
    _control_tasks = _FakeCollection()

    @classmethod
    def reset(cls):
        cls._operations = _FakeCollection()
        cls._control_tasks = _FakeCollection()

    @classmethod
    def _operations_collection(cls):
        return cls._operations

    @classmethod
    def _control_tasks_collection(cls):
        return cls._control_tasks

    @classmethod
    def _get_firestore_client(cls):
        return _FakeFirestoreClientInstance(cls._operations, cls._control_tasks)

    @classmethod
    def _events_collection(cls, operation_id: str):
        return cls._operations.document(operation_id).collection('events')

    @classmethod
    def _artifacts_collection(cls, operation_id: str):
        return cls._operations.document(operation_id).collection('artifacts')


class OperationServiceTestCase(unittest.TestCase):
    def setUp(self):
        TestOperationService.reset()
        self.history_patcher = patch(
            'services.operation_service.HistoryService.add_history',
            autospec=True,
        )
        self.history_patcher.start()

    def tearDown(self):
        self.history_patcher.stop()

    def test_create_operation_sets_pending_approval_and_control_task(self):
        control_task = TestOperationService.ensure_control_task(
            control_task_id='knowledge_reset',
            kind='rag_ingest',
            title='Reset knowledge base',
            schedule='manual',
            owner='system',
        )

        operation = TestOperationService.create_operation(
            'user-1',
            'rag_ingest',
            {'storage_path': 'uploads/docs', 'reset': True},
            control_task_id=control_task['id'],
        )

        self.assertEqual(operation['status'], 'awaiting_approval')
        self.assertEqual(operation['control_task_id'], 'knowledge_reset')
        self.assertEqual(operation['approval_state']['state'], 'pending')

        events = TestOperationService.list_operation_events('user-1', operation['job_id'])
        event_types = [event['type'] for event in events]
        self.assertIn('operation.created', event_types)
        self.assertIn('approval.requested', event_types)

    def test_approve_operation_moves_back_to_queue(self):
        operation = TestOperationService.create_operation(
            'user-1',
            'ml_train',
            {
                'storage_path': 'uploads/train.csv',
                'overwrite_existing': True,
            },
        )
        updated = TestOperationService.approve_operation(
            'user-1',
            operation['job_id'],
            approved=True,
            message='approved for overwrite',
        )

        self.assertIsNotNone(updated)
        self.assertEqual(updated['status'], 'queued')
        self.assertEqual(updated['approval_state']['state'], 'approved')

        events = TestOperationService.list_operation_events('user-1', operation['job_id'])
        self.assertEqual(events[-1]['type'], 'approval.resolved')
        self.assertEqual(events[-1]['status'], 'queued')

    def test_progress_and_success_record_steps_events_and_artifacts(self):
        operation = TestOperationService.create_operation(
            'user-1',
            'analysis',
            {'storage_path': 'uploads/data.csv'},
        )

        TestOperationService.mark_running(operation['job_id'], progress=5, message='Operation started')
        TestOperationService.update_progress(
            operation['job_id'],
            30,
            'Preparing dataset analysis workflow',
            phase='prepare_dataset',
        )
        TestOperationService.update_progress(
            operation['job_id'],
            75,
            'Generating report',
            phase='generate_report',
        )
        TestOperationService.mark_succeeded(
            operation['job_id'],
            {
                'report_path': 'reports/analysis.md',
                'metrics': {'runtime_ms': 3210},
            },
        )

        updated = TestOperationService.get_operation('user-1', operation['job_id'])
        self.assertEqual(updated['status'], 'succeeded')
        self.assertEqual(updated['current_step']['phase'], 'generate_report')
        self.assertEqual(updated['current_step']['status'], 'succeeded')
        self.assertEqual(updated['metrics']['runtime_ms'], 3210)
        self.assertTrue(any(step['phase'] == 'prepare_dataset' for step in updated['steps']))
        self.assertTrue(any(step['phase'] == 'generate_report' for step in updated['steps']))
        self.assertTrue(any(artifact['type'] == 'report' for artifact in updated['artifacts']))

        events = TestOperationService.list_operation_events('user-1', operation['job_id'])
        event_types = [event['type'] for event in events]
        self.assertIn('step.started', event_types)
        self.assertIn('step.progress', event_types)
        self.assertIn('artifact.published', event_types)
        self.assertEqual(events[-1]['type'], 'operation.completed')

    def test_claim_dispatch_moves_queued_operation_to_dispatching_once(self):
        operation = TestOperationService.create_operation(
            'user-1',
            'analysis',
            {'storage_path': 'uploads/data.csv'},
        )

        claimed = TestOperationService.claim_dispatch(operation['job_id'])
        duplicate = TestOperationService.claim_dispatch(operation['job_id'])

        self.assertIsNotNone(claimed)
        self.assertEqual(claimed['status'], 'dispatching')
        self.assertIsNotNone(duplicate)
        self.assertEqual(duplicate['status'], 'dispatching')

        events = TestOperationService.list_operation_events('user-1', operation['job_id'])
        self.assertIn('operation.dispatched', [event['type'] for event in events])

    def test_get_operation_marks_timed_out_running_step_failed(self):
        operation = TestOperationService.create_operation(
            'user-1',
            'ml_train',
            {'storage_path': 'uploads/train.csv'},
        )

        started_at = datetime(2026, 4, 8, 7, 57, 27, tzinfo=timezone.utc)
        running_step = {
            'phase': 'dataset',
            'tool_name': 'prepare_dataset',
            'status': 'running',
            'progress': 25,
            'message': 'Preparing sequence data',
            'started_at': started_at.isoformat(),
            'ended_at': None,
            'duration_ms': None,
            'execution_target': 'light_worker',
            'timeout_s': 300,
            'retry_policy': {'max_attempts': 3, 'backoff': 'exponential'},
        }
        TestOperationService._operations.document(operation['job_id']).set(
            {
                'status': 'running',
                'progress': 25,
                'started_at': started_at,
                'status_message': 'Preparing sequence data',
                'current_step': running_step,
                'steps': [running_step],
            },
            merge=True,
        )

        timed_out_at = started_at + timedelta(minutes=10)
        with patch.object(TestOperationService, '_now_iso', return_value=timed_out_at.isoformat()):
            updated = TestOperationService.get_operation('user-1', operation['job_id'])

        self.assertIsNotNone(updated)
        self.assertEqual(updated['status'], 'failed')
        self.assertEqual(updated['error']['code'], 'TASK_TIMEOUT')
        self.assertEqual(updated['current_step']['status'], 'failed')
        self.assertTrue(updated['error']['message'].startswith("Step 'prepare_dataset' timed out"))

        events = TestOperationService.list_operation_events('user-1', operation['job_id'])
        event_types = [event['type'] for event in events]
        self.assertIn('step.completed', event_types)
        self.assertIn('operation.failed', event_types)


if __name__ == '__main__':
    unittest.main()
