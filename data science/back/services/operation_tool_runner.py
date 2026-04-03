"""Internal operation tool execution surface for future orchestrators."""

from __future__ import annotations

import io
from typing import Any, Callable, Dict

import pandas as pd

from services.analysis_pipeline_service import AnalysisPipelineService
from services.analysis_service import AnalysisService
from services.external_data_service import ExternalDataService
from services.job_workflows import (
    run_optimization_workflow,
    run_rag_ingest_workflow,
)
from services.ml_service import EnergyPredictor
from services.operation_tools import get_tool_contract
from services.storage_service import StorageService
from utils.exceptions import ValidationError


def _load_dataframe(storage_path: str) -> pd.DataFrame:
    if not storage_path:
        raise ValidationError('缺少 storage_path')
    storage = StorageService()
    if not storage.file_exists(storage_path):
        raise ValidationError('文件不存在')
    file_bytes = storage.download_file(storage_path)
    return pd.read_csv(io.BytesIO(file_bytes))


def _prepare_dataset(payload: Dict[str, Any]) -> Dict[str, Any]:
    storage_path = str(payload.get('storage_path') or '').strip()
    df = _load_dataframe(storage_path)
    return {
        'status': 'succeeded',
        'output': {
            'storage_path': storage_path,
            'rows': int(df.shape[0]),
            'columns': list(map(str, df.columns)),
        },
        'metrics': {'row_count': int(df.shape[0]), 'column_count': int(df.shape[1])},
        'artifacts': [],
    }


def _profile_dataset(payload: Dict[str, Any]) -> Dict[str, Any]:
    uid = str(payload.get('requested_by') or payload.get('uid') or 'system')
    storage_path = str(payload.get('storage_path') or '').strip()
    filename = payload.get('filename')
    result = AnalysisPipelineService.run_csv_analysis(
        uid=uid,
        storage_path=storage_path,
        filename=filename,
        save_to_storage=bool(payload.get('save_to_storage', True)),
    )
    return {
        'status': 'succeeded',
        'output': result,
        'metrics': dict(result.get('performance') or {}),
        'artifacts': result.get('artifacts') or [],
    }


def _run_quality_checks(payload: Dict[str, Any]) -> Dict[str, Any]:
    df = _load_dataframe(str(payload.get('storage_path') or '').strip())
    result = AnalysisService.perform_quality_check(df)
    return {
        'status': 'succeeded' if result.get('success') else 'failed',
        'output': result,
        'metrics': {'row_count': int(df.shape[0])},
        'artifacts': [],
        'error': None if result.get('success') else result.get('message'),
    }


def _run_stat_tests(payload: Dict[str, Any]) -> Dict[str, Any]:
    df = _load_dataframe(str(payload.get('storage_path') or '').strip())
    result = AnalysisService.perform_statistical_tests(df)
    return {
        'status': 'succeeded' if result.get('success') else 'failed',
        'output': result,
        'metrics': {'row_count': int(df.shape[0])},
        'artifacts': [],
        'error': None if result.get('success') else result.get('message'),
    }


def _fetch_external_data(_: Dict[str, Any]) -> Dict[str, Any]:
    success = ExternalDataService().fetch_and_publish()
    return {
        'status': 'succeeded' if success else 'failed',
        'output': {'success': success},
        'metrics': {},
        'artifacts': [
            {
                'type': 'dataset',
                'name': 'Processed energy dataset',
                'uri': 'data/processed/cleaned_energy_data_all.csv',
                'metadata': {'source': 'scheduled-fetch'},
            }
        ] if success else [],
        'error': None if success else 'fetch_and_publish returned False',
    }


def _train_forecast_model(payload: Dict[str, Any]) -> Dict[str, Any]:
    predictor = EnergyPredictor()
    metrics = predictor.train_model(
        data_path=payload.get('storage_path'),
        n_estimators=int(payload.get('n_estimators', 100) or 100),
        use_firebase_storage=bool(payload.get('use_firebase_storage', True)),
    )
    return {
        'status': 'succeeded',
        'output': metrics,
        'metrics': metrics,
        'artifacts': [
            {
                'type': 'model',
                'name': 'Forecast model',
                'uri': predictor.firebase_model_path,
                'metadata': {'model_type': metrics.get('model_type')},
            }
        ],
    }


def _optimize_schedule(payload: Dict[str, Any]) -> Dict[str, Any]:
    uid = str(payload.get('requested_by') or payload.get('uid') or 'system')
    result = run_optimization_workflow(uid, payload)
    return {
        'status': 'succeeded',
        'output': result,
        'metrics': dict(result.get('summary') or {}),
        'artifacts': result.get('artifacts') or [],
    }


def _generate_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    summary = str(payload.get('summary') or payload.get('message') or 'Report generated')
    return {
        'status': 'succeeded',
        'output': {'summary': summary, 'source': payload},
        'metrics': {},
        'artifacts': [],
    }


def _publish_artifacts(payload: Dict[str, Any]) -> Dict[str, Any]:
    artifacts = payload.get('artifacts')
    if not isinstance(artifacts, list):
        artifacts = []
    return {
        'status': 'succeeded',
        'output': {'artifacts': artifacts},
        'metrics': {'artifact_count': len(artifacts)},
        'artifacts': artifacts,
    }


def _ingest_knowledge_base(payload: Dict[str, Any]) -> Dict[str, Any]:
    uid = str(payload.get('requested_by') or payload.get('uid') or 'system')
    result = run_rag_ingest_workflow(uid, payload)
    return {
        'status': 'succeeded',
        'output': result,
        'metrics': dict(result.get('stats') or {}),
        'artifacts': result.get('artifacts') or [],
    }


_EXECUTORS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    'fetch_external_data': _fetch_external_data,
    'prepare_dataset': _prepare_dataset,
    'profile_dataset': _profile_dataset,
    'run_quality_checks': _run_quality_checks,
    'run_stat_tests': _run_stat_tests,
    'train_forecast_model': _train_forecast_model,
    'optimize_schedule': _optimize_schedule,
    'generate_report': _generate_report,
    'publish_artifacts': _publish_artifacts,
    'ingest_knowledge_base': _ingest_knowledge_base,
}


def execute_operation_tool(tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    contract = get_tool_contract(tool_name)
    if contract is None:
        raise ValidationError(f'Unsupported tool: {tool_name}')
    executor = _EXECUTORS.get(tool_name)
    if executor is None:
        raise ValidationError(f'Tool contract registered but executor not implemented: {tool_name}')

    result = executor(payload)
    return {
        'tool': contract.to_projection(),
        'status': result.get('status', 'succeeded'),
        'output': result.get('output') or {},
        'artifacts': result.get('artifacts') or [],
        'metrics': result.get('metrics') or {},
        'error': result.get('error'),
    }
