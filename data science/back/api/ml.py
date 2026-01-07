"""
机器学习 API 路由
处理模型训练和预测请求，优化以防止 GAE 60秒超时

基于 course_essence.json 的 Week 13 & 14: 需求分析与严谨实现
"""

from flask import Blueprint, jsonify, request
from services.firebase_service import require_auth
from services.ml_service import MLService, MLServiceError, MemoryError as MLMemoryError
from services.explainability_service import ExplainabilityService
from services.deep_learning_service import DeepLearningService
from services.storage_service import StorageService
from services.history_service import HistoryService
from utils.exceptions import ValidationError
from middleware.rate_limit import rate_limit
import logging
import io
import pandas as pd
import time
import gc
import base64
import tempfile
import os

logger = logging.getLogger(__name__)

ml_bp = Blueprint('ml', __name__, url_prefix='/api/ml')


@ml_bp.route('/train', methods=['POST', 'OPTIONS'])
@rate_limit(max_requests=5, window_seconds=300)  # 5分钟内最多5次训练请求
@require_auth
def train_model():
    """
    训练机器学习模型
    
    请求:
        - Method: POST
        - Headers: Authorization: Bearer <Firebase ID Token>
        - Body: JSON
          {
            "storage_path": "uploads/user123/data.csv",
            "target_column": "price",
            "problem_type": "regression",  # 'regression', 'classification', 'clustering'
            "model_name": "gradient_boosting",  # 可选: 'gradient_boosting', 'linear'
            "n_clusters": 3  # 可选: 仅用于聚类
          }
    
    响应:
        {
            "success": true,
            "model_path": "gs://bucket/models/user123/model_xxx.joblib",
            "metrics": {
                "r2": 0.85,
                "rmse": 12.3,
                "cv_score": 0.83
            },
            "features_importance": [
                {"feature": "feature1", "importance": 0.35},
                ...
            ],
            "training_samples": 5000,
            "training_time_seconds": 15.2,
            "warning": "已对大数据集进行科学采样..."
        }
    """
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        start_time = time.time()
        user = request.user
        uid = user.get('uid')
        data = request.get_json()
        
        # Step 1: 参数校验
        logger.info(f"[{uid}] 收到模型训练请求")
        
        if not data:
            raise ValidationError('请求体不能为空')
        
        storage_path = data.get('storage_path')
        target_column = data.get('target_column')
        problem_type = data.get('problem_type')
        model_name = data.get('model_name')
        n_clusters = data.get('n_clusters')
        
        # 必需参数校验
        if not storage_path:
            raise ValidationError('缺少参数: storage_path')
        
        if not problem_type:
            raise ValidationError('缺少参数: problem_type')
        
        if problem_type not in ['regression', 'classification', 'clustering']:
            raise ValidationError(f"无效的 problem_type: {problem_type}")
        
        if problem_type != 'clustering' and not target_column:
            raise ValidationError(f"{problem_type} 问题需要指定 target_column")
        
        logger.info(f"[{uid}] 训练参数: storage_path={storage_path}, "
                   f"target={target_column}, type={problem_type}, model={model_name}")
        
        # Step 2: 文件存在性校验
        storage = StorageService()
        
        if not storage.file_exists(storage_path):
            raise ValidationError(f'文件不存在: {storage_path}')
        
        # Step 3: 预读 Header 验证目标列
        if problem_type != 'clustering':
            try:
                file_bytes = storage.download_file(storage_path)
                header_stream = io.BytesIO(file_bytes)
                
                # 只读取第一行检查列名
                header_df = pd.read_csv(header_stream, nrows=1)
                
                if target_column not in header_df.columns:
                    available_columns = ', '.join(header_df.columns.tolist())
                    raise ValidationError(
                        f"目标列 '{target_column}' 不存在。"
                        f"可用列: {available_columns}"
                    )
                
                logger.info(f"[{uid}] 目标列验证通过")
                
                # 清理内存
                del header_df
                del header_stream
                gc.collect()
                
            except pd.errors.ParserError as e:
                raise ValidationError(f'CSV 解析错误: {str(e)}')
        
        # Step 4: Resource Management - 下载并优化内存
        logger.info(f"[{uid}] 开始加载数据...")
        load_start = time.time()
        
        file_bytes = storage.download_file(storage_path)
        file_stream = io.BytesIO(file_bytes)
        
        # 读取 CSV
        df = pd.read_csv(file_stream)
        
        load_time = time.time() - load_start
        logger.info(f"[{uid}] 数据加载完成: {df.shape} ({load_time:.2f}s)")
        
        # 立即清理
        del file_bytes
        del file_stream
        gc.collect()
        
        # 数据量检查
        if len(df) < 10:
            raise ValidationError('数据量太少，至少需要 10 行数据')
        
        # Step 5: 调用 MLService 训练
        logger.info(f"[{uid}] 开始训练模型...")
        train_start = time.time()
        
        try:
            result = MLService.train_model(
                df=df,
                target_col=target_column if problem_type != 'clustering' else None,
                problem_type=problem_type,
                model_name=model_name,
                n_clusters=n_clusters
            )
            
            train_time = time.time() - train_start
            logger.info(f"[{uid}] 模型训练完成 ({train_time:.2f}s)")
            
        except MLMemoryError as e:
            logger.error(f"[{uid}] 内存不足: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'MEMORY_ERROR',
                'message': '数据集过大，超出内存限制。请尝试使用较小的数据集。'
            }), 413
        
        except MLServiceError as e:
            logger.error(f"[{uid}] 训练失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'TRAINING_ERROR',
                'message': f'模型训练失败: {str(e)}'
            }), 400
        
        # 清理 DataFrame
        del df
        gc.collect()
        
        # Step 6: 保存模型到 GCS
        logger.info(f"[{uid}] 保存模型...")
        save_start = time.time()
        
        pipeline = result['pipeline']
        model_type = result['model_type']
        
        model_path = MLService.save_model(
            pipeline=pipeline,
            storage_service=storage,
            uid=uid,
            model_name=f"{problem_type}_{model_type}"
        )
        
        save_time = time.time() - save_start
        logger.info(f"[{uid}] 模型保存完成 ({save_time:.2f}s)")
        
        # Step 7: 记录历史
        try:
            history_service = HistoryService()
            history_service.add_history(
                uid=uid,
                action='model_training',
                details={
                    'problem_type': problem_type,
                    'model_type': model_type,
                    'target_column': target_column,
                    'model_path': model_path,
                    'metrics': result['metrics'],
                    'training_samples': result['training_samples']
                },
                status='success'
            )
        except Exception as e:
            logger.warning(f"[{uid}] 历史记录失败: {str(e)}")
        
        # Step 8: 构建响应
        total_time = time.time() - start_time
        
        response = {
            'success': True,
            'model_path': model_path,
            'metrics': result['metrics'],
            'features_importance': result.get('features_importance'),
            'training_samples': result['training_samples'],
            'training_time_seconds': round(result['training_time_seconds'], 2),
            'total_time_seconds': round(total_time, 2),
            'model_type': model_type,
            'problem_type': problem_type
        }
        
        # 添加采样警告（如果有）
        if result.get('warning'):
            response['warning'] = result['warning']
        
        logger.info(f"[{uid}] 训练请求完成 (总耗时: {total_time:.2f}s)")
        
        return jsonify(response), 200
    
    except ValidationError as e:
        logger.warning(f"参数校验失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'VALIDATION_ERROR',
            'message': str(e)
        }), 400
    
    except Exception as e:
        logger.error(f"训练请求异常: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'SERVER_ERROR',
            'message': f'服务器错误: {str(e)}'
        }), 500
    
    finally:
        # 最终清理
        gc.collect()


@ml_bp.route('/predict', methods=['POST', 'OPTIONS'])
@rate_limit(max_requests=50, window_seconds=60)
@require_auth
def predict():
    """
    使用已训练的模型进行预测
    
    请求:
        - Method: POST
        - Headers: Authorization: Bearer <Firebase ID Token>
        - Body: JSON
          {
            "model_path": "gs://bucket/models/user123/model_xxx.joblib",
            "input_data": [
              {
                "feature1": 10,
                "feature2": "value",
                ...
              }
            ]
            或者
            "storage_path": "uploads/user123/test_data.csv"  # 批量预测
          }
    
    响应:
        {
            "success": true,
            "predictions": [25.3, 30.1, ...],
            "probabilities": [[0.2, 0.8], ...],  # 仅分类
            "n_samples": 100
        }
    """
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        start_time = time.time()
        user = request.user
        uid = user.get('uid')
        data = request.get_json()
        
        logger.info(f"[{uid}] 收到预测请求")
        
        # 参数校验
        if not data:
            raise ValidationError('请求体不能为空')
        
        model_path = data.get('model_path')
        input_data = data.get('input_data')
        storage_path = data.get('storage_path')
        
        if not model_path:
            raise ValidationError('缺少参数: model_path')
        
        if not input_data and not storage_path:
            raise ValidationError('需要提供 input_data 或 storage_path')
        
        # 加载模型
        logger.info(f"[{uid}] 加载模型: {model_path}")
        storage = StorageService()
        
        try:
            pipeline = MLService.load_model(storage, model_path)
        except MLServiceError as e:
            raise ValidationError(f'模型加载失败: {str(e)}')
        
        # 准备输入数据
        if storage_path:
            # 从文件加载
            logger.info(f"[{uid}] 从文件加载预测数据: {storage_path}")
            
            if not storage.file_exists(storage_path):
                raise ValidationError(f'文件不存在: {storage_path}')
            
            file_bytes = storage.download_file(storage_path)
            file_stream = io.BytesIO(file_bytes)
            input_df = pd.read_csv(file_stream)
            
            del file_bytes
            del file_stream
            gc.collect()
            
        else:
            # 从 JSON 构建 DataFrame
            input_df = pd.DataFrame(input_data)
        
        logger.info(f"[{uid}] 预测数据形状: {input_df.shape}")
        
        # 数据量限制（防止超时）
        if len(input_df) > 10000:
            raise ValidationError('单次预测最多支持 10000 条数据')
        
        # 执行预测
        logger.info(f"[{uid}] 开始预测...")
        pred_start = time.time()
        
        try:
            result = MLService.predict(pipeline, input_df)
        except MLServiceError as e:
            raise ValidationError(f'预测失败: {str(e)}')
        
        pred_time = time.time() - pred_start
        logger.info(f"[{uid}] 预测完成 ({pred_time:.2f}s)")
        
        # 清理
        del input_df
        del pipeline
        gc.collect()
        
        # 记录历史
        try:
            history_service = HistoryService()
            history_service.add_history(
                uid=uid,
                action='model_prediction',
                details={
                    'model_path': model_path,
                    'n_samples': result['n_samples']
                },
                status='success'
            )
        except Exception as e:
            logger.warning(f"[{uid}] 历史记录失败: {str(e)}")
        
        total_time = time.time() - start_time
        result['prediction_time_seconds'] = round(pred_time, 2)
        result['total_time_seconds'] = round(total_time, 2)
        
        logger.info(f"[{uid}] 预测请求完成 (总耗时: {total_time:.2f}s)")
        
        return jsonify(result), 200
    
    except ValidationError as e:
        logger.warning(f"参数校验失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'VALIDATION_ERROR',
            'message': str(e)
        }), 400
    
    except Exception as e:
        logger.error(f"预测请求异常: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'SERVER_ERROR',
            'message': f'服务器错误: {str(e)}'
        }), 500
    
    finally:
        gc.collect()


@ml_bp.route('/models', methods=['GET', 'OPTIONS'])
@rate_limit(max_requests=30, window_seconds=60)
@require_auth
def list_models():
    """
    列出用户的所有已训练模型
    
    请求:
        - Method: GET
        - Headers: Authorization: Bearer <Firebase ID Token>
    
    响应:
        {
            "success": true,
            "models": [
                {
                    "path": "models/user123/model_xxx.joblib",
                    "name": "model_xxx.joblib",
                    "created_at": "2024-01-01"
                }
            ]
        }
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        user = request.user
        uid = user.get('uid')
        
        logger.info(f"[{uid}] 列出模型")
        
        storage = StorageService()
        prefix = f"models/{uid}/"
        
        model_files = storage.list_files(prefix=prefix)
        
        models = [
            {
                'path': file_path,
                'name': file_path.split('/')[-1],
                'created_at': file_path.split('_')[-1].replace('.joblib', '')
            }
            for file_path in model_files
            if file_path.endswith('.joblib')
        ]
        
        logger.info(f"[{uid}] 找到 {len(models)} 个模型")
        
        return jsonify({
            'success': True,
            'models': models,
            'count': len(models)
        }), 200
    
    except Exception as e:
        logger.error(f"列出模型失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'SERVER_ERROR',
            'message': f'服务器错误: {str(e)}'
        }), 500


@ml_bp.route('/model-info', methods=['POST', 'OPTIONS'])
@rate_limit(max_requests=30, window_seconds=60)
@require_auth
def get_model_info():
    """
    获取模型详细信息（不加载完整模型）
    
    请求:
        - Method: POST
        - Headers: Authorization: Bearer <Firebase ID Token>
        - Body: JSON
          {
            "model_path": "gs://bucket/models/user123/model_xxx.joblib"
          }
    
    响应:
        {
            "success": true,
            "info": {
                "problem_type": "regression",
                "model_type": "HistGradientBoostingRegressor",
                "feature_names": ["feature1", "feature2", ...]
            }
        }
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        user = request.user
        uid = user.get('uid')
        data = request.get_json()
        
        if not data or 'model_path' not in data:
            raise ValidationError('缺少参数: model_path')
        
        model_path = data['model_path']
        
        logger.info(f"[{uid}] 获取模型信息: {model_path}")
        
        storage = StorageService()
        pipeline = MLService.load_model(storage, model_path)
        
        # 提取基本信息（不执行预测）
        info = {
            'model_type': type(pipeline).__name__
        }
        
        # 尝试提取更多信息
        if hasattr(pipeline, 'named_steps'):
            model = pipeline.named_steps.get('model')
            if model:
                info['model_type'] = type(model).__name__
        
        del pipeline
        gc.collect()
        
        return jsonify({
            'success': True,
            'info': info
        }), 200
    
    except Exception as e:
        logger.error(f"获取模型信息失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'SERVER_ERROR',
            'message': f'服务器错误: {str(e)}'
        }), 500


# ================================================================
# 超参数调优 API (Phase 1 新增)
# ================================================================

@ml_bp.route('/tune', methods=['POST', 'OPTIONS'])
@rate_limit(max_requests=2, window_seconds=3600)  # 每小时最多 2 次调参请求
@require_auth
def tune_hyperparameters():
    """
    使用 Optuna 进行超参数调优 (独立于训练流程)
    
    请求:
        - Method: POST
        - Headers: Authorization: Bearer <Firebase ID Token>
        - Body: JSON
          {
            "model_type": "lightgbm",  # 'lightgbm', 'xgboost', 'randomforest'
            "n_trials": 30,            # Optuna 试验次数 (默认 30)
            "storage_path": "data/processed/cleaned_energy_data_all.csv"  # 可选
          }
    
    响应:
        {
            "success": true,
            "best_params": {...},
            "best_score": 12.5,
            "n_trials": 30,
            "tuning_time_seconds": 120.5
        }
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        start_time = time.time()
        user = request.user
        uid = user.get('uid')
        data = request.get_json() or {}
        
        logger.info(f"[{uid}] 收到超参数调优请求")
        
        # 参数解析
        model_type = data.get('model_type', 'lightgbm')
        n_trials = min(int(data.get('n_trials', 30)), 100)  # 限制最大 100 次
        storage_path = data.get('storage_path')
        
        # 模型类型校验
        valid_types = ['lightgbm', 'xgboost', 'randomforest']
        if model_type.lower() not in valid_types:
            raise ValidationError(f"无效的 model_type: {model_type}. 支持: {valid_types}")
        
        logger.info(f"[{uid}] 调优参数: model_type={model_type}, n_trials={n_trials}")
        
        # 导入必要模块
        try:
            import optuna
            from optuna.pruners import MedianPruner
            from sklearn.model_selection import TimeSeriesSplit, cross_val_score
            optuna.logging.set_verbosity(optuna.logging.WARNING)
        except ImportError:
            raise ValidationError("Optuna 未安装，无法进行超参数调优")
        
        # 加载数据
        from services.storage_service import StorageService
        storage = StorageService()
        
        data_path = storage_path or 'data/processed/cleaned_energy_data_all.csv'
        
        if not storage.file_exists(data_path):
            raise ValidationError(f"数据文件不存在: {data_path}")
        
        logger.info(f"[{uid}] 加载数据: {data_path}")
        file_bytes = storage.download_file(data_path)
        df = pd.read_csv(io.BytesIO(file_bytes), parse_dates=['Date'])
        
        del file_bytes
        gc.collect()
        
        logger.info(f"[{uid}] 数据加载完成: {df.shape}")
        
        # 准备特征 (与 ml_service 保持一致)
        from services.ml_service import EnergyPredictor
        predictor = EnergyPredictor()
        
        # 动态检测可用特征
        available_features = [col for col in predictor.base_feature_columns if col in df.columns]
        for col in predictor.enhanced_feature_columns:
            if col in df.columns:
                available_features.append(col)
        
        # 清理 NaN
        df = df.dropna(subset=available_features + [predictor.target_column])
        
        X = df[available_features]
        y = df[predictor.target_column]
        
        logger.info(f"[{uid}] 特征数量: {len(available_features)}, 样本数量: {len(X)}")
        
        # 时间序列拆分
        tscv = TimeSeriesSplit(n_splits=5)
        
        # 创建 Optuna 目标函数
        def objective(trial):
            if model_type.lower() == 'lightgbm':
                from lightgbm import LGBMRegressor
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 100, 500),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.15, log=True),
                    'num_leaves': trial.suggest_int('num_leaves', 20, 150),
                    'max_depth': trial.suggest_int('max_depth', 5, 25),
                    'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                    'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                }
                model = LGBMRegressor(**params, random_state=42, n_jobs=-1, verbose=-1)
                
            elif model_type.lower() == 'xgboost':
                from xgboost import XGBRegressor
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 100, 500),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.15, log=True),
                    'max_depth': trial.suggest_int('max_depth', 3, 15),
                    'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                    'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                }
                model = XGBRegressor(**params, random_state=42, n_jobs=-1, verbosity=0)
                
            else:
                from sklearn.ensemble import RandomForestRegressor
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 100, 400),
                    'max_depth': trial.suggest_int('max_depth', 5, 30),
                    'min_samples_split': trial.suggest_int('min_samples_split', 2, 15),
                    'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 8),
                }
                model = RandomForestRegressor(**params, random_state=42, n_jobs=-1)
            
            scores = cross_val_score(
                model, X, y,
                cv=tscv,
                scoring='neg_mean_absolute_error',
                n_jobs=1
            )
            return -scores.mean()
        
        # 运行 Optuna
        logger.info(f"[{uid}] 开始 Optuna 调优 ({n_trials} trials)...")
        
        study = optuna.create_study(
            direction='minimize',
            pruner=MedianPruner(n_startup_trials=5),
            sampler=optuna.samplers.TPESampler(seed=42)
        )
        
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False, n_jobs=1)
        
        tuning_time = time.time() - start_time
        
        # 保存调参日志
        try:
            log_df = study.trials_dataframe()
            log_content = log_df.to_csv(index=False)
            log_path = f'tuning_logs/{uid}/tuning_log_{model_type}.csv'
            storage.bucket.blob(log_path).upload_from_string(
                log_content, content_type='text/csv'
            )
            logger.info(f"[{uid}] 调参日志已保存: {log_path}")
        except Exception as log_err:
            logger.warning(f"[{uid}] 保存调参日志失败: {log_err}")
        
        logger.info(f"[{uid}] 调优完成: best_score={study.best_value:.4f}")
        
        # 清理
        del df, X, y
        gc.collect()
        
        return jsonify({
            'success': True,
            'model_type': model_type,
            'best_params': study.best_params,
            'best_score': round(study.best_value, 4),
            'n_trials': n_trials,
            'tuning_time_seconds': round(tuning_time, 2)
        }), 200
        
    except ValidationError as e:
        logger.warning(f"参数校验失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'VALIDATION_ERROR',
            'message': str(e)
        }), 400
    
    except Exception as e:
        logger.error(f"调优请求异常: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'SERVER_ERROR',
            'message': f'服务器错误: {str(e)}'
        }), 500
    
    finally:
        gc.collect()


# ================================================================
# 可解释性 API (Phase 2 新增)
# ================================================================

@ml_bp.route('/explain', methods=['POST', 'OPTIONS'])
@rate_limit(max_requests=10, window_seconds=60)
@require_auth
def explain_model():
    """
    生成模型解释 (SHAP)
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        user = request.user
        uid = user.get('uid')
        data = request.get_json() or {}
        
        model_path = data.get('model_path')
        storage_path = data.get('storage_path')
        
        if not model_path or not storage_path:
            raise ValidationError('缺少参数: model_path 或 storage_path')

        logger.info(f"[{uid}] 开始解释模型: {model_path}")

        storage = StorageService()
        
        # 加载模型
        pipeline = MLService.load_model(storage, model_path)
        # 尝试获取内部模型
        model = pipeline
        if hasattr(pipeline, 'named_steps'):
             model = pipeline.named_steps.get('model', pipeline)

        # 加载数据
        file_bytes = storage.download_file(storage_path)
        df = pd.read_csv(io.BytesIO(file_bytes))
        
        # 简单选取数值特征用于解释
        # 实际生产中应复用训练时的预处理逻辑
        X = df.select_dtypes(include='number').iloc[:100]
        
        # 使用 ExplainabilityService
        explainer_service = ExplainabilityService()
        
        # 计算 SHAP
        shap_values, expected_value, feature_names = explainer_service.calculate_shap_values(
            model=model,
            X=X,
            feature_names=X.columns.tolist(),
            model_type='tree' # default
        )
        
        # 生成摘要图
        summary_plot = explainer_service.plot_summary(shap_values, X)
        
        # 上传图表
        timestamp = int(time.time())
        plot_path = f"explanations/{uid}/{timestamp}_summary.png"
        storage.bucket.blob(plot_path).upload_from_string(base64.b64decode(summary_plot), content_type='image/png')
        
        return jsonify({
            'success': True,
            'shap_values_summary': 'SHAP values calculated',
            'plot_url': f"gs://{storage.bucket_name}/{plot_path}"
        }), 200

    except Exception as e:
        logger.error(f"解释模型失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'SERVER_ERROR', 'message': str(e)}), 500


# ================================================================
# 深度学习 API (Phase 3 新增)
# ================================================================

@ml_bp.route('/deep/train', methods=['POST', 'OPTIONS'])
@rate_limit(max_requests=2, window_seconds=600)
@require_auth
def train_deep_model():
    """
    训练深度学习模型 (LSTM/GRU)
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
        
    try:
        user = request.user
        uid = user.get('uid')
        data = request.get_json() or {}
        
        storage_path = data.get('storage_path')
        model_type = data.get('model_type', 'lstm')
        target_col = data.get('target_column')
        lookback = int(data.get('lookback', 24))
        horizon = int(data.get('horizon', 1))
        epochs = int(data.get('epochs', 10))
        
        if not storage_path or not target_col:
            raise ValidationError("缺少 storage_path 或 target_column")
            
        logger.info(f"[{uid}] 开始训练深度模型 {model_type}")
        
        dl_service = DeepLearningService()
        if not dl_service.is_available():
             raise ValidationError("深度学习依赖未安装")

        storage = StorageService()
        file_bytes = storage.download_file(storage_path)
        df = pd.read_csv(io.BytesIO(file_bytes), parse_dates=['Date']) # 假设有 Date 列，或由用户指定时间列
        
        # 训练
        result = dl_service.train_model(
            data=df,
            target_col=target_col,
            model_type=model_type,
            lookback=lookback,
            horizon=horizon,
            epochs=epochs
        )
        
        model = result['model']
        history = result['history']
        metrics = result['metrics']
        
        # 保存模型 (.keras)
        timestamp = int(time.time())
        with tempfile.NamedTemporaryFile(suffix='.keras', delete=False) as tmp:
            model.save(tmp.name)
            tmp_path = tmp.name
            
        remote_path = f"models/{uid}/dl_{model_type}_{timestamp}.keras"
        storage.upload_file(tmp_path, remote_path)
        os.remove(tmp_path)
        
        return jsonify({
            'success': True,
            'model_path': remote_path,
            'metrics': metrics,
            'history': history.history if hasattr(history, 'history') else history
        }), 200
        
    except Exception as e:
        logger.error(f"深度学习训练失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'SERVER_ERROR', 'message': str(e)}), 500

