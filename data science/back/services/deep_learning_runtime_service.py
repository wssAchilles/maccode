"""Reusable deep-learning runtime shared by Cloud Run fallback and Vertex jobs."""

from __future__ import annotations

import io
import json
import os
import tempfile
import time
from typing import Any, Callable, Dict, Optional

import joblib
import numpy as np
import pandas as pd

from services.deep_learning_service import DeepLearningService
from services.history_service import HistoryService
from services.storage_service import StorageService
from utils.exceptions import ValidationError

ProgressCallback = Callable[
    [int, str, str, Optional[Dict[str, Any]]],
    None,
]
_TRAINING_PLACEHOLDER_PATHS = {'', 'demo_data.csv', 'demo.csv', 'sample.csv'}
_TRAINING_PLACEHOLDER_TARGETS = {'', 'load', 'target', 'label'}


def _emit_progress(
    callback: Optional[ProgressCallback],
    progress: int,
    message: str,
    phase: str,
    metrics: Optional[Dict[str, Any]] = None,
) -> None:
    if callback is None:
        return
    callback(progress, message, phase, metrics)


def _normalize_storage_path(value: Any) -> str:
    raw = str(value or '').strip()
    if not raw:
        return ''
    if raw.startswith('gs://'):
        without_scheme = raw[len('gs://'):]
        _, _, blob_name = without_scheme.partition('/')
        return blob_name
    return raw.lstrip('/')


def _history_dataset_candidates(uid: str) -> list[str]:
    candidates: list[str] = []
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


def _resolve_training_storage_path(
    uid: str,
    raw_storage_path: Any,
    storage: StorageService,
) -> str:
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


def execute_deep_learning_training(
    uid: str,
    payload: Dict[str, Any],
    *,
    run_id: Optional[str] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> Dict[str, Any]:
    requested_storage_path = payload.get('storage_path')
    model_type = (payload.get('model_type') or 'lstm').lower()
    requested_target_col = payload.get('target_column')
    window_size = int(payload.get('window_size', payload.get('lookback', 24)))
    horizon = int(payload.get('horizon', 1))
    epochs = int(payload.get('epochs', 10))
    batch_size = int(payload.get('batch_size', 32))
    run_label = str(run_id or int(time.time()))

    availability = DeepLearningService.is_available()
    use_tensorflow = bool(availability.get('tensorflow'))

    _emit_progress(progress_callback, 35, 'Loading training dataset', 'dataset')
    storage = StorageService()
    storage_path = _resolve_training_storage_path(uid, requested_storage_path, storage)
    file_bytes = storage.download_file(storage_path)
    df = pd.read_csv(io.BytesIO(file_bytes))
    target_col = _resolve_training_target_column(requested_target_col, df)
    if target_col not in df.columns:
        raise ValidationError(f"目标列 '{target_col}' 不存在")

    numeric_features = [
        col
        for col in df.select_dtypes(include=[np.number]).columns.tolist()
        if col != target_col
    ]
    if not numeric_features:
        numeric_features = [target_col]

    _emit_progress(
        progress_callback,
        50,
        'Building supervised sequences',
        'sequencing',
        {
            'dataset_rows': len(df),
            'feature_count': len(numeric_features),
            'window_size': window_size,
            'horizon': horizon,
        },
    )
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
    _emit_progress(
        progress_callback,
        60,
        'Initializing model architecture',
        'model_init',
        {
            'training_samples': len(X_train),
            'validation_samples': 0 if X_val is None else len(X_val),
        },
    )
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

        _emit_progress(progress_callback, 68, 'Training neural network weights', 'training')

        def _on_epoch_progress(
            current_epoch: int,
            total_epochs: int,
            metrics: Dict[str, float],
        ) -> None:
            progress = min(84, 68 + int((current_epoch / max(total_epochs, 1)) * 16))
            _emit_progress(
                progress_callback,
                progress,
                f'Training epoch {current_epoch}/{total_epochs}',
                'training',
                metrics,
            )

        result = DeepLearningService.train_model(
            model,
            X_train,
            y_train,
            X_val=X_val,
            y_val=y_val,
            epochs=epochs,
            batch_size=batch_size,
            verbose=0,
            progress_callback=_on_epoch_progress,
        )
    else:
        from sklearn.metrics import mean_absolute_error, mean_squared_error
        from sklearn.neural_network import MLPRegressor
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        runtime_backend = 'sklearn_mlp_fallback'
        artifact_suffix = '.joblib'
        _emit_progress(
            progress_callback,
            64,
            'TensorFlow unavailable, using lightweight sklearn fallback',
            'fallback_backend',
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
        _emit_progress(progress_callback, 70, 'Training fallback neural regressor', 'training')
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
    _emit_progress(
        progress_callback,
        86,
        'Persisting trained model artifact',
        'artifact_upload',
    )
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

    run_base = f'models/{uid}/runs/{run_label}'
    metrics_payload = {
        'train_loss': result.get('train_loss'),
        'train_mae': result.get('train_mae'),
        'val_loss': result.get('val_loss'),
        'val_mae': result.get('val_mae'),
        'epochs_trained': result.get('epochs_trained'),
        'training_samples': len(X_train),
        'validation_samples': 0 if X_val is None else len(X_val),
    }
    history_payload = result.get('history', {})
    manifest_path = f'{run_base}/manifest.json'
    metrics_path = f'{run_base}/metrics.json'
    history_path = f'{run_base}/history.json'

    payload_result = {
        'run_id': run_label,
        'model_path': remote_path,
        'storage_path': storage_path,
        'metrics': metrics_payload,
        'history': history_payload,
        'model_type': model_type,
        'target_column': target_col,
        'runtime_backend': runtime_backend,
        'artifact_format': artifact_suffix.lstrip('.'),
        'manifest_path': manifest_path,
        'metrics_path': metrics_path,
        'history_path': history_path,
    }
    payload_result['artifacts'] = [
        {
            'type': 'model',
            'name': 'Trained model',
            'uri': remote_path,
            'metadata': {
                'model_type': model_type,
                'artifact_format': payload_result['artifact_format'],
            },
        },
        {
            'type': 'report',
            'name': 'Training manifest',
            'uri': manifest_path,
            'metadata': {'format': 'json', 'run_id': run_label},
        },
        {
            'type': 'report',
            'name': 'Training metrics',
            'uri': metrics_path,
            'metadata': {'format': 'json', 'run_id': run_label},
        },
        {
            'type': 'report',
            'name': 'Training history',
            'uri': history_path,
            'metadata': {'format': 'json', 'run_id': run_label},
        },
    ]

    manifest_payload = {
        'uid': uid,
        'run_id': run_label,
        'created_at': int(time.time()),
        'input': {
            'storage_path': storage_path,
            'model_type': model_type,
            'target_column': target_col,
            'window_size': window_size,
            'horizon': horizon,
            'epochs': epochs,
            'batch_size': batch_size,
        },
        'result': payload_result,
    }
    storage.upload_file(
        json.dumps(manifest_payload, ensure_ascii=False, indent=2).encode('utf-8'),
        manifest_path,
        content_type='application/json',
    )
    storage.upload_file(
        json.dumps(metrics_payload, ensure_ascii=False, indent=2).encode('utf-8'),
        metrics_path,
        content_type='application/json',
    )
    storage.upload_file(
        json.dumps(history_payload, ensure_ascii=False, indent=2).encode('utf-8'),
        history_path,
        content_type='application/json',
    )

    _emit_progress(
        progress_callback,
        94,
        'Packaging training metrics and artifact metadata',
        'packaging',
        metrics_payload,
    )
    return payload_result
