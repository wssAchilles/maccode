"""Tests for the control-task planning service."""

from __future__ import annotations

import copy
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACK_ROOT = Path(__file__).resolve().parents[2]
if str(BACK_ROOT) not in sys.path:
    sys.path.insert(0, str(BACK_ROOT))

SERVER_TIMESTAMP = object()

google_module = types.ModuleType('google')
cloud_module = types.ModuleType('google.cloud')
firestore_module = types.ModuleType('google.cloud.firestore')
firestore_v1_module = types.ModuleType('google.cloud.firestore_v1')


class _FirestoreClient:
    def __init__(self, *args, **kwargs):
        pass


firestore_module.Client = _FirestoreClient
firestore_v1_module.SERVER_TIMESTAMP = SERVER_TIMESTAMP
cloud_module.firestore = firestore_module
cloud_module.firestore_v1 = firestore_v1_module
google_module.cloud = cloud_module

sys.modules.setdefault('google', google_module)
sys.modules.setdefault('google.cloud', cloud_module)
sys.modules.setdefault('google.cloud.firestore', firestore_module)
sys.modules.setdefault('google.cloud.firestore_v1', firestore_v1_module)

from services.control_task_service import ControlTaskService


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


class _FakeDocumentReference:
    def __init__(self, collection, doc_id: str):
        self._collection = collection
        self.id = doc_id

    def get(self):
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


class _FakeCollection:
    def __init__(self):
        self._docs = {}

    def document(self, doc_id: str):
        return _FakeDocumentReference(self, doc_id)

    def stream(self):
        return [_FakeSnapshot(doc_id, data, exists=True) for doc_id, data in self._docs.items()]


class _FakeFirestoreClient:
    def __init__(self, *, tasks, jobs):
        self._tasks = tasks
        self._jobs = jobs

    def collection(self, name: str):
        if name == 'control_tasks':
            return self._tasks
        if name == 'jobs':
            return self._jobs
        raise KeyError(name)


class TestControlTaskService(ControlTaskService):
    _tasks = _FakeCollection()
    _jobs = _FakeCollection()

    @classmethod
    def reset(cls):
        cls._tasks = _FakeCollection()
        cls._jobs = _FakeCollection()
        cls._defaults_seeded = False

    @classmethod
    def _collection(cls):
        return cls._tasks

    @staticmethod
    def _get_firestore_client():
        return _FakeFirestoreClient(tasks=TestControlTaskService._tasks, jobs=TestControlTaskService._jobs)

    @classmethod
    def ensure_default_control_tasks(cls) -> None:
        return None


class ControlTaskServiceTestCase(unittest.TestCase):
    def setUp(self):
        TestControlTaskService.reset()

    def test_ensure_and_get_control_task(self):
        created = TestControlTaskService.ensure_control_task(
            control_task_id='fetch_data_hourly',
            kind='scheduler',
            operation_type='fetch_data',
            title='每小时抓取',
            schedule='every 1 hours',
            default_input={'task_name': 'fetch_data'},
            dependencies=['dataset_ready'],
            owner='system',
        )

        self.assertEqual(created['id'], 'fetch_data_hourly')
        self.assertEqual(created['kind'], 'scheduler')
        self.assertEqual(created['operation_type'], 'fetch_data')
        self.assertEqual(created['default_input']['task_name'], 'fetch_data')
        self.assertEqual(created['dependencies'], ['dataset_ready'])
        self.assertTrue(created['enabled'])

        fetched = TestControlTaskService.get_control_task('fetch_data_hourly')
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched['title'], '每小时抓取')
        self.assertEqual(fetched['schedule'], 'every 1 hours')

    def test_list_control_tasks_filters_and_sorts(self):
        TestControlTaskService.ensure_control_task(
            control_task_id='train_daily',
            kind='scheduler',
            operation_type='train_model',
            title='每日训练',
            owner='system',
            enabled=True,
        )
        TestControlTaskService.ensure_control_task(
            control_task_id='rag_manual',
            kind='manual',
            operation_type='rag_ingest',
            title='知识库重建',
            owner='ops',
            enabled=False,
        )

        # Simulate an older update time so sorting is deterministic.
        TestControlTaskService._tasks._docs['train_daily']['updated_at'] = datetime.now(
            timezone.utc,
        ) - timedelta(days=1)

        manual_tasks = TestControlTaskService.list_control_tasks(kind='manual', limit=10)
        self.assertEqual(len(manual_tasks), 1)
        self.assertEqual(manual_tasks[0]['id'], 'rag_manual')

        disabled_tasks = TestControlTaskService.list_control_tasks(enabled=False, limit=10)
        self.assertEqual(len(disabled_tasks), 1)
        self.assertEqual(disabled_tasks[0]['owner'], 'ops')

        ordered = TestControlTaskService.list_control_tasks(limit=10)
        ordered_ids = {item['id'] for item in ordered}
        self.assertEqual(ordered_ids, {'rag_manual', 'train_daily'})

    def test_set_control_task_enabled_updates_enabled_flag(self):
        TestControlTaskService.ensure_control_task(
            control_task_id='fetch_data_hourly',
            kind='scheduler',
            operation_type='fetch_data',
            title='每小时抓取',
            enabled=True,
        )

        updated = TestControlTaskService.set_control_task_enabled(
            'fetch_data_hourly',
            enabled=False,
        )

        self.assertIsNotNone(updated)
        self.assertFalse(updated['enabled'])

    def test_list_control_tasks_enriches_runtime_fields(self):
        TestControlTaskService.ensure_control_task(
            control_task_id='train_model_daily',
            kind='scheduler',
            operation_type='train_model',
            title='每日模型重训',
            schedule='every day 04:00 UTC',
            dependencies=['dataset_ready'],
        )
        TestControlTaskService.ensure_control_task(
            control_task_id='dataset_ready',
            kind='scheduler',
            operation_type='fetch_data',
            title='数据已准备',
            enabled=True,
        )
        TestControlTaskService._jobs.document('op-1').set(
            {
                'job_id': 'op-1',
                'operation_id': 'op-1',
                'type': 'train_model',
                'status': 'awaiting_approval',
                'progress': 0,
                'attempt_count': 0,
                'max_attempts': 3,
                'requested_by': 'tester',
                'control_task_id': 'train_model_daily',
                'submitted_at': datetime.now(timezone.utc),
            }
        )

        tasks = TestControlTaskService.list_control_tasks(limit=10)
        task = next(item for item in tasks if item['id'] == 'train_model_daily')

        self.assertEqual(task['dependency_state'], 'ready')
        self.assertEqual(task['dependency_summary'], '依赖已就绪')
        self.assertIsNotNone(task['next_run_at'])
        self.assertEqual(task['latest_operation']['status'], 'awaiting_approval')

    def test_set_control_task_approval_policy_updates_policy_projection(self):
        TestControlTaskService.ensure_control_task(
            control_task_id='train_model_daily',
            kind='scheduler',
            operation_type='train_model',
            title='每日模型重训',
            approval_policy={'required': False, 'mode': 'auto'},
        )

        updated = TestControlTaskService.set_control_task_approval_policy(
            'train_model_daily',
            approval_policy={'required': True, 'mode': 'manual'},
        )

        self.assertIsNotNone(updated)
        self.assertTrue(updated['approval_policy']['required'])
        self.assertEqual(updated['approval_policy']['mode'], 'manual')

    def test_update_control_task_definition_fields(self):
        TestControlTaskService.ensure_control_task(
            control_task_id='train_model_daily',
            kind='scheduler',
            operation_type='train_model',
            title='每日模型重训',
            schedule='every day 04:00 UTC',
            owner='system',
            default_input={'window_days': 30},
        )

        updated = TestControlTaskService.update_control_task(
            'train_model_daily',
            dependencies=['dataset_ready', 'weather_ready'],
            approval_policy={
                'required': True,
                'mode': 'manual',
                'reason': '高成本重训需要审批',
            },
            schedule='every day 05:00 UTC',
            owner='mlops',
            default_input={'window_days': 60, 'retrain': True},
        )

        self.assertIsNotNone(updated)
        self.assertEqual(updated['dependencies'], ['dataset_ready', 'weather_ready'])
        self.assertTrue(updated['approval_policy']['required'])
        self.assertEqual(updated['approval_policy']['reason'], '高成本重训需要审批')
        self.assertEqual(updated['schedule'], 'every day 05:00 UTC')
        self.assertEqual(updated['owner'], 'mlops')
        self.assertEqual(updated['default_input']['window_days'], 60)
        self.assertTrue(updated['default_input']['retrain'])


if __name__ == '__main__':
    unittest.main()
