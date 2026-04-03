"""Default planning-layer control-task definitions."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List


_DEFAULT_CONTROL_TASKS: List[Dict[str, Any]] = [
    {
        'control_task_id': 'fetch_data_hourly',
        'kind': 'scheduler',
        'operation_type': 'fetch_data',
        'title': '每小时外部数据抓取',
        'schedule': 'every 1 hours',
        'default_input': {'task_name': 'fetch_data'},
        'dependencies': [],
        'approval_policy': {'required': False, 'mode': 'auto'},
        'enabled': True,
        'owner': 'data-platform',
    },
    {
        'control_task_id': 'train_model_daily',
        'kind': 'scheduler',
        'operation_type': 'train_model',
        'title': '每日预测模型重训',
        'schedule': 'every day 04:00 UTC',
        'default_input': {
            'task_name': 'train_model',
            'n_estimators': 100,
            'use_firebase_storage': True,
        },
        'dependencies': ['fetch_data_hourly'],
        'approval_policy': {'required': False, 'mode': 'auto'},
        'enabled': True,
        'owner': 'ml-platform',
    },
    {
        'control_task_id': 'analysis_manual',
        'kind': 'manual',
        'operation_type': 'analysis',
        'title': '按需数据分析',
        'schedule': 'manual',
        'default_input': {'operation_type': 'analysis'},
        'dependencies': ['fetch_data_hourly'],
        'approval_policy': {'required': False, 'mode': 'auto'},
        'enabled': True,
        'owner': 'analytics',
    },
    {
        'control_task_id': 'optimization_manual',
        'kind': 'manual',
        'operation_type': 'optimization',
        'title': '按需优化调度',
        'schedule': 'manual',
        'default_input': {'operation_type': 'optimization'},
        'dependencies': ['train_model_daily'],
        'approval_policy': {
            'required': True,
            'mode': 'manual',
            'reason': '覆盖优化结果或运行大规模求解前需要审批',
        },
        'enabled': True,
        'owner': 'operations-research',
    },
    {
        'control_task_id': 'ml_train_manual',
        'kind': 'manual',
        'operation_type': 'ml_train',
        'title': '按需深度学习训练',
        'schedule': 'manual',
        'default_input': {'operation_type': 'ml_train'},
        'dependencies': ['fetch_data_hourly'],
        'approval_policy': {
            'required': True,
            'mode': 'manual',
            'reason': '重训深度学习模型会占用较高算力并覆盖产物',
        },
        'enabled': True,
        'owner': 'ml-platform',
    },
    {
        'control_task_id': 'rag_ingest_manual',
        'kind': 'manual',
        'operation_type': 'rag_ingest',
        'title': '按需知识库入库',
        'schedule': 'manual',
        'default_input': {'operation_type': 'rag_ingest'},
        'dependencies': [],
        'approval_policy': {
            'required': True,
            'mode': 'manual',
            'reason': '重建知识库或重置集合前需要审批',
        },
        'enabled': True,
        'owner': 'knowledge-platform',
    },
]


def list_default_control_tasks() -> List[Dict[str, Any]]:
    """Return deep-copied default task definitions for system bootstrap."""

    return [deepcopy(item) for item in _DEFAULT_CONTROL_TASKS]
