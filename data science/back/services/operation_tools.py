"""Operation tool contracts and phase-to-tool mapping."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class OperationToolContract:
    """Declarative contract for a workflow tool."""

    name: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    timeout_s: int
    retry_policy: Dict[str, Any]
    approval_policy: Dict[str, Any]
    execution_target: str
    concurrency_key: str
    artifact_policy: Dict[str, Any]

    def to_projection(self) -> Dict[str, Any]:
        return asdict(self)


_DEFAULT_RETRY_POLICY = {'max_attempts': 3, 'backoff': 'exponential'}
_NO_APPROVAL = {'required': False, 'mode': 'auto'}
_MANUAL_APPROVAL = {'required': True, 'mode': 'manual'}
_DEFAULT_ARTIFACT_POLICY = {'mode': 'reference', 'retain': True}


STANDARD_TOOL_CONTRACTS: Dict[str, OperationToolContract] = {
    'fetch_external_data': OperationToolContract(
        name='fetch_external_data',
        input_schema={'type': 'object', 'properties': {}},
        output_schema={'type': 'object', 'properties': {'success': {'type': 'boolean'}}},
        timeout_s=300,
        retry_policy=_DEFAULT_RETRY_POLICY,
        approval_policy=_NO_APPROVAL,
        execution_target='light_worker',
        concurrency_key='scheduler:fetch_external_data',
        artifact_policy=_DEFAULT_ARTIFACT_POLICY,
    ),
    'prepare_dataset': OperationToolContract(
        name='prepare_dataset',
        input_schema={'type': 'object', 'properties': {'storage_path': {'type': 'string'}}},
        output_schema={'type': 'object', 'properties': {'storage_path': {'type': 'string'}}},
        timeout_s=300,
        retry_policy=_DEFAULT_RETRY_POLICY,
        approval_policy=_NO_APPROVAL,
        execution_target='light_worker',
        concurrency_key='dataset:prepare',
        artifact_policy=_DEFAULT_ARTIFACT_POLICY,
    ),
    'profile_dataset': OperationToolContract(
        name='profile_dataset',
        input_schema={'type': 'object', 'properties': {'storage_path': {'type': 'string'}}},
        output_schema={'type': 'object', 'properties': {'analysis_result': {'type': 'object'}}},
        timeout_s=600,
        retry_policy=_DEFAULT_RETRY_POLICY,
        approval_policy=_NO_APPROVAL,
        execution_target='light_worker',
        concurrency_key='dataset:profile',
        artifact_policy=_DEFAULT_ARTIFACT_POLICY,
    ),
    'run_quality_checks': OperationToolContract(
        name='run_quality_checks',
        input_schema={'type': 'object', 'properties': {'storage_path': {'type': 'string'}}},
        output_schema={'type': 'object', 'properties': {'quality_analysis': {'type': 'object'}}},
        timeout_s=300,
        retry_policy=_DEFAULT_RETRY_POLICY,
        approval_policy=_NO_APPROVAL,
        execution_target='light_worker',
        concurrency_key='dataset:quality',
        artifact_policy=_DEFAULT_ARTIFACT_POLICY,
    ),
    'run_stat_tests': OperationToolContract(
        name='run_stat_tests',
        input_schema={'type': 'object', 'properties': {'storage_path': {'type': 'string'}}},
        output_schema={'type': 'object', 'properties': {'statistical_tests': {'type': 'object'}}},
        timeout_s=300,
        retry_policy=_DEFAULT_RETRY_POLICY,
        approval_policy=_NO_APPROVAL,
        execution_target='light_worker',
        concurrency_key='dataset:stats',
        artifact_policy=_DEFAULT_ARTIFACT_POLICY,
    ),
    'train_forecast_model': OperationToolContract(
        name='train_forecast_model',
        input_schema={'type': 'object', 'properties': {'storage_path': {'type': 'string'}}},
        output_schema={'type': 'object', 'properties': {'metrics': {'type': 'object'}}},
        timeout_s=1800,
        retry_policy=_DEFAULT_RETRY_POLICY,
        approval_policy=_MANUAL_APPROVAL,
        execution_target='heavy_worker',
        concurrency_key='model:train',
        artifact_policy=_DEFAULT_ARTIFACT_POLICY,
    ),
    'evaluate_model': OperationToolContract(
        name='evaluate_model',
        input_schema={'type': 'object', 'properties': {'model_path': {'type': 'string'}}},
        output_schema={'type': 'object', 'properties': {'metrics': {'type': 'object'}}},
        timeout_s=600,
        retry_policy=_DEFAULT_RETRY_POLICY,
        approval_policy=_NO_APPROVAL,
        execution_target='light_worker',
        concurrency_key='model:evaluate',
        artifact_policy=_DEFAULT_ARTIFACT_POLICY,
    ),
    'optimize_schedule': OperationToolContract(
        name='optimize_schedule',
        input_schema={'type': 'object', 'properties': {'target_date': {'type': 'string'}}},
        output_schema={'type': 'object', 'properties': {'schedule': {'type': 'array'}}},
        timeout_s=900,
        retry_policy=_DEFAULT_RETRY_POLICY,
        approval_policy=_MANUAL_APPROVAL,
        execution_target='light_worker',
        concurrency_key='optimizer:schedule',
        artifact_policy=_DEFAULT_ARTIFACT_POLICY,
    ),
    'generate_report': OperationToolContract(
        name='generate_report',
        input_schema={'type': 'object', 'properties': {'operation_id': {'type': 'string'}}},
        output_schema={'type': 'object', 'properties': {'summary': {'type': 'string'}}},
        timeout_s=180,
        retry_policy=_DEFAULT_RETRY_POLICY,
        approval_policy=_NO_APPROVAL,
        execution_target='light_worker',
        concurrency_key='report:generate',
        artifact_policy=_DEFAULT_ARTIFACT_POLICY,
    ),
    'publish_artifacts': OperationToolContract(
        name='publish_artifacts',
        input_schema={'type': 'object', 'properties': {'artifacts': {'type': 'array'}}},
        output_schema={'type': 'object', 'properties': {'artifacts': {'type': 'array'}}},
        timeout_s=180,
        retry_policy=_DEFAULT_RETRY_POLICY,
        approval_policy=_MANUAL_APPROVAL,
        execution_target='light_worker',
        concurrency_key='artifact:publish',
        artifact_policy=_DEFAULT_ARTIFACT_POLICY,
    ),
    'ingest_knowledge_base': OperationToolContract(
        name='ingest_knowledge_base',
        input_schema={'type': 'object', 'properties': {'storage_path': {'type': 'string'}}},
        output_schema={'type': 'object', 'properties': {'stats': {'type': 'object'}}},
        timeout_s=1800,
        retry_policy=_DEFAULT_RETRY_POLICY,
        approval_policy=_MANUAL_APPROVAL,
        execution_target='heavy_worker',
        concurrency_key='rag:ingest',
        artifact_policy=_DEFAULT_ARTIFACT_POLICY,
    ),
    'prepare_compute_rollout_change': OperationToolContract(
        name='prepare_compute_rollout_change',
        input_schema={
            'type': 'object',
            'properties': {
                'component': {'type': 'string'},
                'target_policy': {'type': 'object'},
            },
        },
        output_schema={'type': 'object', 'properties': {'preview_policy': {'type': 'object'}}},
        timeout_s=120,
        retry_policy=_DEFAULT_RETRY_POLICY,
        approval_policy=_MANUAL_APPROVAL,
        execution_target='light_worker',
        concurrency_key='governance:compute:prepare',
        artifact_policy=_DEFAULT_ARTIFACT_POLICY,
    ),
    'apply_compute_rollout_change': OperationToolContract(
        name='apply_compute_rollout_change',
        input_schema={
            'type': 'object',
            'properties': {
                'component': {'type': 'string'},
                'target_policy': {'type': 'object'},
            },
        },
        output_schema={'type': 'object', 'properties': {'after_policy': {'type': 'object'}}},
        timeout_s=180,
        retry_policy=_DEFAULT_RETRY_POLICY,
        approval_policy=_MANUAL_APPROVAL,
        execution_target='light_worker',
        concurrency_key='governance:compute:apply',
        artifact_policy=_DEFAULT_ARTIFACT_POLICY,
    ),
    'prepare_compute_benchmark': OperationToolContract(
        name='prepare_compute_benchmark',
        input_schema={
            'type': 'object',
            'properties': {
                'component': {'type': 'string'},
                'sample_rows': {'type': 'integer'},
            },
        },
        output_schema={'type': 'object', 'properties': {'component': {'type': 'string'}}},
        timeout_s=120,
        retry_policy=_DEFAULT_RETRY_POLICY,
        approval_policy=_NO_APPROVAL,
        execution_target='operation_target',
        concurrency_key='governance:compute:benchmark:prepare',
        artifact_policy=_DEFAULT_ARTIFACT_POLICY,
    ),
    'run_compute_benchmark': OperationToolContract(
        name='run_compute_benchmark',
        input_schema={
            'type': 'object',
            'properties': {
                'component': {'type': 'string'},
                'sample_rows': {'type': 'integer'},
            },
        },
        output_schema={'type': 'object', 'properties': {'metrics': {'type': 'object'}}},
        timeout_s=900,
        retry_policy=_DEFAULT_RETRY_POLICY,
        approval_policy=_NO_APPROVAL,
        execution_target='operation_target',
        concurrency_key='governance:compute:benchmark:run',
        artifact_policy=_DEFAULT_ARTIFACT_POLICY,
    ),
    'publish_compute_benchmark': OperationToolContract(
        name='publish_compute_benchmark',
        input_schema={'type': 'object', 'properties': {'artifacts': {'type': 'array'}}},
        output_schema={'type': 'object', 'properties': {'artifacts': {'type': 'array'}}},
        timeout_s=180,
        retry_policy=_DEFAULT_RETRY_POLICY,
        approval_policy=_NO_APPROVAL,
        execution_target='operation_target',
        concurrency_key='governance:compute:benchmark:publish',
        artifact_policy=_DEFAULT_ARTIFACT_POLICY,
    ),
}


PHASE_TOOL_MAP: Dict[str, Dict[str, str]] = {
    'analysis': {
        'dataset': 'prepare_dataset',
        'basic_analysis': 'profile_dataset',
        'quality': 'run_quality_checks',
        'correlation': 'profile_dataset',
        'statistical': 'run_stat_tests',
        'history_archive': 'publish_artifacts',
        'packaging': 'generate_report',
    },
    'optimization': {
        'model_metadata': 'prepare_dataset',
        'forecast': 'prepare_dataset',
        'solver': 'optimize_schedule',
        'aggregation': 'generate_report',
        'explainability': 'evaluate_model',
        'packaging': 'publish_artifacts',
    },
    'ml_train': {
        'dataset': 'prepare_dataset',
        'sequencing': 'prepare_dataset',
        'model_init': 'train_forecast_model',
        'training': 'train_forecast_model',
        'artifact_upload': 'publish_artifacts',
        'packaging': 'evaluate_model',
    },
    'rag_ingest': {
        'fetch_documents': 'prepare_dataset',
        'reset_collection': 'ingest_knowledge_base',
        'parsing': 'ingest_knowledge_base',
        'embedding': 'ingest_knowledge_base',
        'packaging': 'publish_artifacts',
    },
    'fetch_data': {
        'fetch_external_data': 'fetch_external_data',
        'publish_artifacts': 'publish_artifacts',
    },
    'train_model': {
        'prepare_dataset': 'prepare_dataset',
        'train_forecast_model': 'train_forecast_model',
        'publish_artifacts': 'publish_artifacts',
    },
    'compute_rollout_change': {
        'compute_rollout_prepare': 'prepare_compute_rollout_change',
        'compute_rollout_apply': 'apply_compute_rollout_change',
    },
    'compute_benchmark': {
        'compute_benchmark_prepare': 'prepare_compute_benchmark',
        'compute_benchmark_run': 'run_compute_benchmark',
        'compute_benchmark_publish': 'publish_compute_benchmark',
    },
}


def get_tool_contract(tool_name: str) -> Optional[OperationToolContract]:
    return STANDARD_TOOL_CONTRACTS.get(tool_name)


def resolve_tool_name(operation_type: str, phase: str) -> str:
    return PHASE_TOOL_MAP.get(operation_type, {}).get(phase, phase)
