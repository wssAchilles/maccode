"""Long-running workflows executed by the job system."""

from __future__ import annotations

import io
import logging
import os
import re
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
import pandas as pd

from config import Config
from services.analysis_pipeline_service import AnalysisPipelineService
from services.deep_learning_service import DeepLearningService
from services.history_service import HistoryService
from services.ml_service import EnergyPredictor
from services.optimization_service import EnergyOptimizer
from services.rag_service import RAGService
from services.storage_service import StorageService
from utils.exceptions import ValidationError

logger = logging.getLogger(__name__)

_BACK_DIR = Path(__file__).resolve().parent.parent
_TRAINING_PLACEHOLDER_PATHS = {'', 'demo_data.csv', 'demo.csv', 'sample.csv'}
_TRAINING_PLACEHOLDER_TARGETS = {'', 'load', 'target', 'label'}
_RAG_PLACEHOLDER_PATHS = {'', 'docs', 'docs/'}
_RAG_PLACEHOLDER_COLLECTIONS = {'', 'default', 't_docs', 'project_docs'}
_RAG_SUPPORTED_SUFFIXES = {'.txt', '.md', '.json', '.py', '.csv', '.xlsx', '.xls'}


def _job_progress(
    job_id: str | None,
    progress: int,
    message: str,
    *,
    phase: str = 'progress',
) -> None:
    if not job_id:
        return
    from services.job_service import JobService

    JobService.update_progress(job_id, progress, message, phase=phase)


def _generate_importance_interpretation(importance: dict) -> str:
    if not importance:
        return '特征重要性数据不可用'
    feature_names = {
        'Hour': '小时',
        'DayOfWeek': '星期',
        'Temperature': '温度',
        'Price': '电价',
    }
    sorted_items = sorted(importance.items(), key=lambda item: item[1], reverse=True)
    top_feature, top_score = sorted_items[0]
    top_name = feature_names.get(top_feature, top_feature)
    return f'{top_name}是影响负载预测的最重要因素 ({top_score * 100:.1f}%)'


def _normalize_storage_path(value: Any) -> str:
    raw = str(value or '').strip()
    if not raw:
        return ''
    if raw.startswith('gs://'):
        without_scheme = raw[len('gs://'):]
        _, _, blob_name = without_scheme.partition('/')
        return blob_name
    return raw.lstrip('/')


def _history_dataset_candidates(uid: str) -> List[str]:
    candidates: List[str] = []
    for record in HistoryService.get_user_history(uid, limit=20):
        storage_url = _normalize_storage_path(record.get('storage_url'))
        filename = str(record.get('filename') or '').lower()
        if storage_url and (storage_url.lower().endswith('.csv') or filename.endswith('.csv')):
            candidates.append(storage_url)
    return candidates


def _latest_training_storage_path(uid: str, storage: StorageService) -> str:
    for candidate in _history_dataset_candidates(uid):
        if storage.file_exists(candidate):
            return candidate

    for prefix in (f'uploads/{uid}/', 'uploads/'):
        for item in reversed(storage.list_files(prefix)):
            if item.lower().endswith('.csv'):
                return item

    raise ValidationError(
        '未找到可训练的数据资产，请先在数据分析页上传并完成分析，或填写有效的 CSV storage_path。'
    )


def _resolve_training_storage_path(uid: str, raw_storage_path: Any, storage: StorageService) -> str:
    normalized = _normalize_storage_path(raw_storage_path)
    if normalized.lower() not in _TRAINING_PLACEHOLDER_PATHS:
        return normalized
    return _latest_training_storage_path(uid, storage)


def _resolve_training_target_column(raw_target: Any, df: pd.DataFrame) -> str:
    requested = str(raw_target or '').strip()
    if requested and requested in df.columns and requested.lower() not in _TRAINING_PLACEHOLDER_TARGETS:
        return requested

    preferred_columns = [
        'Site_Load',
        'AEP_MW',
        'Load',
        'load',
        'target',
        'Target',
        'y',
        'label',
    ]
    for candidate in preferred_columns:
        if candidate in df.columns:
            return candidate

    numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_columns:
        return numeric_columns[-1]

    available_columns = ', '.join(map(str, df.columns[:8]))
    raise ValidationError(
        f"未能自动识别目标列，请显式填写 target_column。当前可用列包括: {available_columns}"
    )


def _latest_rag_document_path(uid: str, storage: StorageService) -> str:
    prefixes = (f'docs/{uid}/', f'uploads/{uid}/', 'docs/', 'uploads/')
    for prefix in prefixes:
        files = [item for item in storage.list_files(prefix) if Path(item).suffix.lower() in _RAG_SUPPORTED_SUFFIXES]
        if files:
            return sorted(files)[-1]

    raise ValidationError(
        '未找到可构建知识库的文档，请上传 txt/md/json/py/csv/xlsx 文档后再试，或填写有效 storage_path。'
    )


def _resolve_rag_storage_path(uid: str, raw_storage_path: Any, storage: StorageService) -> str:
    normalized = _normalize_storage_path(raw_storage_path)
    if normalized.lower() in _RAG_PLACEHOLDER_PATHS:
        return _latest_rag_document_path(uid, storage)

    if normalized.endswith('/'):
        supported_files = [
            item for item in storage.list_files(normalized)
            if Path(item).suffix.lower() in _RAG_SUPPORTED_SUFFIXES
        ]
        if supported_files:
            return normalized
        raise ValidationError(
            '知识文档目录中没有可解析的 txt/md/json/py/csv/xlsx 文件，请补充文档后再试。'
        )

    if Path(normalized).suffix.lower() not in _RAG_SUPPORTED_SUFFIXES:
        raise ValidationError('知识库仅支持 txt、md、json、py、csv、xlsx 文档作为构建输入。')
    return normalized


def _resolve_rag_collection_name(uid: str, raw_collection: Any, storage_path: str) -> str:
    collection_name = str(raw_collection or '').strip()
    if collection_name.lower() not in _RAG_PLACEHOLDER_COLLECTIONS:
        return collection_name
    stem = Path(storage_path.rstrip('/')).stem
    safe_stem = re.sub(r'[^a-zA-Z0-9_-]+', '_', stem).strip('_')
    return safe_stem[:48] if safe_stem else f'user_{uid[:12]}'


def run_optimization_workflow(
    uid: str,
    payload: Dict[str, Any],
    job_id: str | None = None,
) -> Dict[str, Any]:
    initial_soc = float(payload.get('initial_soc', 0.5))
    target_date = payload.get('target_date')
    temp_forecast = payload.get('temperature_forecast')
    temp_adjust = float(payload.get('temperature_adjust', 0.0))

    if not 0 <= initial_soc <= 1:
        raise ValidationError('initial_soc 必须在 0.0 到 1.0 之间')
    if temp_forecast is not None and (not isinstance(temp_forecast, list) or len(temp_forecast) != 24):
        raise ValidationError('temperature_forecast 必须是包含 24 个值的列表')

    if target_date:
        try:
            target_datetime = datetime.strptime(target_date, '%Y-%m-%d')
            target_datetime = target_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        except ValueError as exc:
            raise ValidationError('target_date 格式错误，应为 YYYY-MM-DD') from exc
    else:
        target_datetime = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        target_date = target_datetime.strftime('%Y-%m-%d')

    battery_capacity = float(payload.get('battery_capacity', Config.BATTERY_CONFIG['capacity']))
    battery_power = float(payload.get('battery_power', Config.BATTERY_CONFIG['max_power']))
    battery_efficiency = float(payload.get('battery_efficiency', Config.BATTERY_CONFIG['efficiency']))

    _job_progress(job_id, 35, 'Loading forecast model metadata', phase='model_metadata')
    model_metadata = EnergyPredictor.get_model_metadata()
    predictor = EnergyPredictor()
    predictor.load_model()
    _job_progress(job_id, 50, 'Generating 24h demand and tariff forecast', phase='forecast')
    predictions = predictor.predict_next_24h(
        start_time=target_datetime,
        temp_forecast_list=temp_forecast,
        temp_adjust_delta=temp_adjust,
    )
    load_profile = [item['predicted_load'] for item in predictions]
    price_profile = [item['price'] for item in predictions]

    optimizer = EnergyOptimizer(
        battery_capacity=battery_capacity,
        max_power=battery_power,
        efficiency=battery_efficiency,
    )
    _job_progress(job_id, 68, 'Running optimization solver', phase='solver')
    result = optimizer.optimize_schedule(
        load_profile=load_profile,
        price_profile=price_profile,
        initial_soc=initial_soc,
    )
    if result['status'] != 'Optimal':
        raise RuntimeError(result.get('error', f"优化求解失败: {result['status']}"))

    avg_load = sum(load_profile) / len(load_profile)
    peak_load = max(load_profile)
    min_load = min(load_profile)

    chart_data = []
    for item in result['schedule']:
        dt = target_datetime + timedelta(hours=item['hour'])
        chart_data.append(
            {
                'hour': item['hour'],
                'datetime': dt.strftime('%Y-%m-%dT%H:%M:%S'),
                'load': round(item['load'], 2),
                'price': item['price'],
                'battery_action': round(item['battery_action'], 2),
                'charge_power': round(item['charge_power'], 2),
                'discharge_power': round(item['discharge_power'], 2),
                'soc': round(item['soc'] * 100, 1),
                'stored_energy': round(item['stored_energy'], 2),
                'grid_power': round(item['load'] + item['battery_action'], 2),
            }
        )

    total_charged = sum(item['charge_power'] for item in result['schedule'])
    total_discharged = sum(item['discharge_power'] for item in result['schedule'])
    total_load = sum(item['load'] for item in result['schedule'])
    charging_hours = [item['hour'] for item in result['schedule'] if item['battery_action'] > 0.01]
    discharging_hours = [item['hour'] for item in result['schedule'] if item['battery_action'] < -0.01]
    _job_progress(job_id, 76, 'Aggregating schedule and cost summary', phase='aggregation')

    payload_result: Dict[str, Any] = {
        'optimization': {
            'status': result['status'],
            'chart_data': chart_data,
            'summary': {
                'total_cost_without_battery': round(result['total_cost_without_battery'], 2),
                'total_cost_with_battery': round(result['total_cost_with_battery'], 2),
                'savings': round(result['savings'], 2),
                'savings_percent': round(result['savings_percent'], 2),
                'total_load': round(total_load, 2),
                'total_charged': round(total_charged, 2),
                'total_discharged': round(total_discharged, 2),
                'peak_load': round(peak_load, 2),
                'min_load': round(min_load, 2),
                'avg_load': round(avg_load, 2),
            },
            'strategy': {
                'charging_hours': charging_hours,
                'discharging_hours': discharging_hours,
                'charging_count': len(charging_hours),
                'discharging_count': len(discharging_hours),
            },
            'diagnostics': result.get('diagnostics'),
            'constraint_hits': result.get('constraint_hits'),
        },
        'prediction': {
            'target_date': target_date,
            'avg_load': round(avg_load, 2),
            'peak_load': round(peak_load, 2),
            'min_load': round(min_load, 2),
        },
        'battery_config': {
            'capacity': battery_capacity,
            'max_power': battery_power,
            'efficiency': battery_efficiency,
            'initial_soc': initial_soc,
        },
    }

    try:
        _job_progress(job_id, 82, 'Computing model explainability', phase='explainability')
        feature_importance = predictor.get_feature_importance()
        payload_result['model_explainability'] = {
            'feature_importance': feature_importance,
            'feature_descriptions': {
                'Hour': '小时 (0-23)',
                'DayOfWeek': '星期几 (0=周一, 6=周日)',
                'Temperature': '温度 (°C)',
                'Price': '电价 (元/kWh)',
            },
            'interpretation': _generate_importance_interpretation(feature_importance),
        }
    except Exception as exc:
        logger.warning('[%s] feature importance unavailable: %s', uid, exc)

    _job_progress(job_id, 92, 'Packaging optimization result payload', phase='packaging')
    payload_result['model_info'] = model_metadata or {
        'model_type': 'Random Forest Regressor',
        'status': 'unknown',
        'data_source': 'CAISO Real-Time Stream',
        'metrics': {},
    }

    HistoryService.add_history(
        uid=uid,
        action='optimization_completed',
        status='success',
        source='optimization',
        title='完成能源优化任务',
        details={
            'target_date': target_date,
            'savings': payload_result['optimization']['summary']['savings'],
            'savings_percent': payload_result['optimization']['summary']['savings_percent'],
        },
    )
    return payload_result


def run_analysis_workflow(
    uid: str,
    payload: Dict[str, Any],
    job_id: str | None = None,
) -> Dict[str, Any]:
    storage_path = payload.get('storage_path')
    filename = payload.get('filename')
    save_to_storage = payload.get('save_to_storage', True)
    if not isinstance(save_to_storage, bool):
        save_to_storage = str(save_to_storage).lower() in ('1', 'true', 'yes', 'on')

    if not storage_path:
        raise ValidationError('缺少参数: storage_path')

    return AnalysisPipelineService.run_csv_analysis(
        uid=uid,
        storage_path=storage_path,
        filename=filename,
        save_to_storage=save_to_storage,
        progress_callback=(
            None
            if job_id is None
            else lambda progress, message, phase: _job_progress(
                job_id,
                progress,
                message,
                phase=phase,
            )
        ),
    )


def run_deep_learning_workflow(
    uid: str,
    payload: Dict[str, Any],
    job_id: str | None = None,
) -> Dict[str, Any]:
    requested_storage_path = payload.get('storage_path')
    model_type = (payload.get('model_type') or 'lstm').lower()
    requested_target_col = payload.get('target_column')
    window_size = int(payload.get('window_size', payload.get('lookback', 24)))
    horizon = int(payload.get('horizon', 1))
    epochs = int(payload.get('epochs', 10))
    batch_size = int(payload.get('batch_size', 32))

    availability = DeepLearningService.is_available()
    use_tensorflow = bool(availability.get('tensorflow'))

    _job_progress(job_id, 35, 'Loading training dataset', phase='dataset')
    storage = StorageService()
    storage_path = _resolve_training_storage_path(uid, requested_storage_path, storage)
    file_bytes = storage.download_file(storage_path)
    df = pd.read_csv(io.BytesIO(file_bytes))
    target_col = _resolve_training_target_column(requested_target_col, df)
    if target_col not in df.columns:
        raise ValidationError(f"目标列 '{target_col}' 不存在")

    numeric_features = [
        col for col in df.select_dtypes(include=[np.number]).columns.tolist() if col != target_col
    ]
    if not numeric_features:
        numeric_features = [target_col]

    _job_progress(job_id, 50, 'Building supervised sequences', phase='sequencing')
    X, y = DeepLearningService.prepare_sequences(
        df=df,
        target_col=target_col,
        feature_cols=numeric_features,
        lookback=window_size,
        horizon=horizon,
    )
    if len(X) < 5:
        raise ValidationError('可用训练样本过少，无法进行深度学习训练')

    split_index = max(1, int(len(X) * 0.8))
    X_train, X_val = X[:split_index], X[split_index:]
    y_train, y_val = y[:split_index], y[split_index:]
    if len(X_val) == 0:
        X_val, y_val = None, None

    runtime_backend = 'tensorflow'
    artifact_suffix = '.keras'
    _job_progress(job_id, 60, 'Initializing model architecture', phase='model_init')
    if use_tensorflow:
        if model_type == 'gru':
            model = DeepLearningService.create_gru_model(
                input_shape=(X.shape[1], X.shape[2]),
                output_size=y.shape[1],
            )
        else:
            model = DeepLearningService.create_lstm_model(
                input_shape=(X.shape[1], X.shape[2]),
                output_size=y.shape[1],
            )
            model_type = 'lstm'

        _job_progress(job_id, 68, 'Training neural network weights', phase='training')
        result = DeepLearningService.train_model(
            model,
            X_train,
            y_train,
            X_val=X_val,
            y_val=y_val,
            epochs=epochs,
            batch_size=batch_size,
            verbose=0,
        )
    else:
        from sklearn.metrics import mean_absolute_error, mean_squared_error
        from sklearn.neural_network import MLPRegressor
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        runtime_backend = 'sklearn_mlp_fallback'
        artifact_suffix = '.joblib'
        _job_progress(
            job_id,
            64,
            'TensorFlow unavailable, using lightweight sklearn fallback',
            phase='fallback_backend',
        )
        train_samples = X_train.reshape((X_train.shape[0], -1))
        val_samples = None if X_val is None else X_val.reshape((X_val.shape[0], -1))
        train_targets = y_train.ravel() if y_train.ndim == 2 and y_train.shape[1] == 1 else y_train
        val_targets = None
        if y_val is not None:
            val_targets = y_val.ravel() if y_val.ndim == 2 and y_val.shape[1] == 1 else y_val
        fallback_model = Pipeline(
            steps=[
                ('scaler', StandardScaler()),
                (
                    'mlp',
                    MLPRegressor(
                        hidden_layer_sizes=(128, 64),
                        max_iter=max(epochs * 20, 200),
                        learning_rate_init=0.001,
                        random_state=42,
                        early_stopping=val_samples is not None and y_val is not None,
                        validation_fraction=0.1,
                        n_iter_no_change=10,
                    ),
                ),
            ]
        )
        _job_progress(job_id, 70, 'Training fallback neural regressor', phase='training')
        fallback_model.fit(train_samples, train_targets)
        train_predictions = np.asarray(fallback_model.predict(train_samples))
        if train_predictions.ndim == 1:
            train_predictions = train_predictions.reshape((-1, 1))
        train_loss = float(mean_squared_error(y_train, train_predictions))
        train_mae = float(mean_absolute_error(y_train, train_predictions))
        result = {
            'success': True,
            'epochs_trained': int(getattr(fallback_model.named_steps['mlp'], 'n_iter_', 0)),
            'train_loss': train_loss,
            'train_mae': train_mae,
            'history': {},
        }
        if val_samples is not None and val_targets is not None and len(val_samples) > 0:
            val_predictions = np.asarray(fallback_model.predict(val_samples))
            if val_predictions.ndim == 1:
                val_predictions = val_predictions.reshape((-1, 1))
            result['val_loss'] = float(mean_squared_error(y_val, val_predictions))
            result['val_mae'] = float(mean_absolute_error(y_val, val_predictions))
        model = fallback_model

    timestamp = int(time.time())
    _job_progress(job_id, 86, 'Persisting trained model artifact', phase='artifact_upload')
    with tempfile.NamedTemporaryFile(suffix=artifact_suffix, delete=False) as tmp:
        if use_tensorflow:
            model.save(tmp.name)
        else:
            joblib.dump(model, tmp.name)
        tmp_path = tmp.name

    remote_path = f'models/{uid}/dl_{model_type}_{timestamp}{artifact_suffix}'
    with open(tmp_path, 'rb') as handle:
        storage.upload_file(handle, remote_path, content_type='application/octet-stream')
    os.remove(tmp_path)

    payload_result = {
        'model_path': remote_path,
        'storage_path': storage_path,
        'metrics': {
            'train_loss': result.get('train_loss'),
            'train_mae': result.get('train_mae'),
            'val_loss': result.get('val_loss'),
            'val_mae': result.get('val_mae'),
            'epochs_trained': result.get('epochs_trained'),
            'training_samples': len(X_train),
        },
        'history': result.get('history', {}),
        'model_type': model_type,
        'target_column': target_col,
        'runtime_backend': runtime_backend,
        'artifact_format': artifact_suffix.lstrip('.'),
    }
    _job_progress(job_id, 94, 'Packaging training metrics and artifact metadata', phase='packaging')

    HistoryService.add_history(
        uid=uid,
        action='deep_learning_completed',
        status='success',
        source='ml_train',
        title=f'完成深度学习训练: {model_type.upper()}',
        details={
            'model_path': remote_path,
            'target_column': target_col,
            'epochs_trained': result.get('epochs_trained'),
            'runtime_backend': runtime_backend,
        },
    )
    return payload_result


def run_rag_ingest_workflow(
    uid: str,
    payload: Dict[str, Any],
    job_id: str | None = None,
) -> Dict[str, Any]:
    requested_storage_path = payload.get('storage_path')
    requested_collection_name = payload.get('collection_name')
    reset = bool(payload.get('reset', False))

    availability = RAGService.is_available()
    if not availability.get('available'):
        raise RuntimeError('RAG 服务当前不可用')

    storage = StorageService()
    storage_path = _resolve_rag_storage_path(uid, requested_storage_path, storage)
    collection_name = _resolve_rag_collection_name(uid, requested_collection_name, storage_path)
    service = RAGService(collection_name=collection_name)
    _job_progress(job_id, 35, 'Fetching source documents', phase='fetch_documents')
    with tempfile.TemporaryDirectory() as temp_dir:
        local_path = os.path.join(temp_dir, 'docs')
        os.makedirs(local_path, exist_ok=True)

        if not storage_path.endswith('/'):
            file_bytes = storage.download_file(storage_path)
            fname = os.path.basename(storage_path)
            with open(os.path.join(local_path, fname), 'wb') as handle:
                handle.write(file_bytes)
        else:
            files = storage.list_files(storage_path)
            for item in files:
                if item.endswith('/'):
                    continue
                file_bytes = storage.download_file(item)
                fname = os.path.basename(item)
                with open(os.path.join(local_path, fname), 'wb') as handle:
                    handle.write(file_bytes)

        if reset:
            _job_progress(job_id, 46, 'Resetting existing knowledge collection', phase='reset_collection')
            service.reset_collection()

        _job_progress(job_id, 58, 'Loading and chunking documents', phase='parsing')
        documents = service.load_documents(local_path)
        _job_progress(job_id, 82, 'Creating embeddings and persisting vectors', phase='embedding')
        count = service.create_embeddings(documents)
        stats = service.get_stats()

    payload_result = {
        'collection': collection_name,
        'count': count,
        'stats': stats,
        'reset': reset,
        'backend': stats.get('backend'),
        'storage_path': storage_path,
    }
    _job_progress(job_id, 94, 'Packaging knowledge-base statistics', phase='packaging')
    HistoryService.add_history(
        uid=uid,
        action='rag_ingest_completed',
        status='success',
        source='rag_ingest',
        title='完成知识库构建',
        details={
            'collection': collection_name,
            'count': count,
            'storage_path': storage_path,
            'backend': stats.get('backend'),
        },
    )
    return payload_result
