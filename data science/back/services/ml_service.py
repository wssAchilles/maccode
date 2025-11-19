"""
机器学习服务
为 GAE F1 (256MB RAM) 优化的精益且强大的 ML Service

核心理念：高效算法 + 科学采样 + 内存优化
基于 course_essence.json 中的数据科学哲学
"""

import pandas as pd
import numpy as np
import joblib
import io
import gc
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# Scikit-learn imports
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, RobustScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.feature_selection import SelectKBest, f_classif, f_regression, SelectFromModel

# Models - 使用内存高效的算法
from sklearn.experimental import enable_hist_gradient_boosting  # noqa
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.linear_model import SGDRegressor, LogisticRegression, Lasso
from sklearn.cluster import MiniBatchKMeans
from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier

# Metrics
from sklearn.metrics import (
    mean_squared_error, r2_score, accuracy_score, 
    f1_score, silhouette_score, mean_absolute_error
)

logger = logging.getLogger(__name__)


class MLServiceError(Exception):
    """ML服务自定义异常"""
    pass


class MemoryError(MLServiceError):
    """内存不足异常"""
    pass


class MLService:
    """
    机器学习服务类
    
    核心特性：
    1. 内存优化 - 数据类型降维
    2. 科学采样 - 保证统计显著性的分层采样
    3. 智能预处理 - 自动化 Pipeline
    4. 高效算法 - HistGradientBoosting, SGD, MiniBatchKMeans
    5. 严谨评估 - 交叉验证
    """
    
    # 模型配置 (Week 08 & 09: ML Best Practices)
    MAX_TRAINING_SAMPLES = 5000  # 科学采样上限
    MAX_CATEGORIES = 20  # OneHot编码最大类别数
    CV_FOLDS = 3  # 交叉验证折数
    RANDOM_STATE = 42  # 保证可复现性
    
    @staticmethod
    def _optimize_memory(df: pd.DataFrame) -> pd.DataFrame:
        """
        内存优化 - 物理缩减数据体积
        
        Week 02 Implementation Tips: 理解向量化和内存管理
        Week 03 Philosophical Core: Garbage in, garbage out
        
        Args:
            df: 原始 DataFrame
            
        Returns:
            优化后的 DataFrame
        """
        logger.info("开始内存优化...")
        initial_memory = df.memory_usage(deep=True).sum() / 1024**2
        
        # 1. Float64 -> Float32
        float_cols = df.select_dtypes(include=['float64']).columns
        if len(float_cols) > 0:
            df[float_cols] = df[float_cols].astype('float32')
            logger.info(f"将 {len(float_cols)} 个 float64 列转为 float32")
        
        # 2. Int64 -> Int32 (如果值域允许)
        int_cols = df.select_dtypes(include=['int64']).columns
        for col in int_cols:
            if df[col].min() >= np.iinfo(np.int32).min and df[col].max() <= np.iinfo(np.int32).max:
                df[col] = df[col].astype('int32')
        
        # 3. Object -> Category (高基数检测)
        object_cols = df.select_dtypes(include=['object']).columns
        for col in object_cols:
            num_unique = df[col].nunique()
            num_total = len(df[col])
            
            # 如果唯一值 < 50% 总行数，转为 category
            if num_unique / num_total < 0.5:
                df[col] = df[col].astype('category')
                logger.info(f"将列 '{col}' 转为 category (唯一值: {num_unique})")
        
        final_memory = df.memory_usage(deep=True).sum() / 1024**2
        logger.info(f"内存优化完成: {initial_memory:.2f}MB -> {final_memory:.2f}MB "
                   f"(减少 {(1 - final_memory/initial_memory)*100:.1f}%)")
        
        return df
    
    @staticmethod
    def _scientific_sampling(
        df: pd.DataFrame, 
        target_col: str, 
        problem_type: str,
        max_samples: int = MAX_TRAINING_SAMPLES
    ) -> Tuple[pd.DataFrame, bool]:
        """
        科学采样 - 保留统计特征
        
        Week 04 Philosophical Core: 统计思维允许我们量化不确定性
        Week 08 Critical Limitations: 需要大量高质量数据，但要避免过拟合
        
        Args:
            df: 数据集
            target_col: 目标列
            problem_type: 问题类型 ('regression', 'classification', 'clustering')
            max_samples: 最大采样数
            
        Returns:
            (采样后的df, 是否进行了采样)
        """
        if len(df) <= max_samples:
            return df, False
        
        logger.info(f"数据集包含 {len(df)} 行，超过阈值 {max_samples}，进行科学采样...")
        
        try:
            if problem_type == 'classification':
                # 分层采样 - 保留类别分布 (Week 04 Mathematical Essence)
                sampled_df, _ = train_test_split(
                    df,
                    train_size=max_samples,
                    stratify=df[target_col],
                    random_state=MLService.RANDOM_STATE
                )
                logger.info(f"使用分层采样保留类别分布，采样 {len(sampled_df)} 行")
                
            elif problem_type == 'regression':
                # 随机采样
                sampled_df = df.sample(n=max_samples, random_state=MLService.RANDOM_STATE)
                logger.info(f"使用随机采样，采样 {len(sampled_df)} 行")
                
            else:  # clustering
                # 对于聚类，随机采样即可
                sampled_df = df.sample(n=max_samples, random_state=MLService.RANDOM_STATE)
                logger.info(f"聚类任务：随机采样 {len(sampled_df)} 行")
            
            return sampled_df, True
            
        except Exception as e:
            logger.warning(f"科学采样失败: {str(e)}，使用简单随机采样")
            sampled_df = df.sample(n=max_samples, random_state=MLService.RANDOM_STATE)
            return sampled_df, True
    
    @staticmethod
    def _build_preprocessing_pipeline(
        numeric_features: List[str],
        categorical_features: List[str]
    ) -> ColumnTransformer:
        """
        构建智能预处理 Pipeline
        
        Week 03 Code Preferences: 使用 scikit-learn Pipelines 实现可复现预处理
        Week 03 Mathematical Essence: 统计方法处理缺失值和异常值
        
        Args:
            numeric_features: 数值特征列表
            categorical_features: 类别特征列表
            
        Returns:
            ColumnTransformer
        """
        # 数值特征处理: Median Imputation + RobustScaler
        # RobustScaler 使用中位数和 IQR，对异常值更稳健 (Week 03)
        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', RobustScaler())
        ])
        
        # 类别特征处理: Constant Imputation + OneHotEncoding
        # 限制类别数防止内存爆炸
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
            ('onehot', OneHotEncoder(
                handle_unknown='ignore',
                max_categories=MLService.MAX_CATEGORIES,
                sparse_output=False  # 对于小数据集，dense更快
            ))
        ])
        
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, numeric_features),
                ('cat', categorical_transformer, categorical_features)
            ],
            remainder='drop'
        )
        
        logger.info(f"构建预处理 Pipeline: {len(numeric_features)} 数值特征, "
                   f"{len(categorical_features)} 类别特征")
        
        return preprocessor
    
    @staticmethod
    def _select_model(problem_type: str, model_name: Optional[str] = None):
        """
        选择模型 - The "Smart" Choice
        
        Week 09 Implementation Tips: 优先使用集成方法而非单棵树
        Week 08 Decision Heuristic: 预测准确性优先时使用ML
        
        Args:
            problem_type: 问题类型
            model_name: 指定模型名称（可选）
            
        Returns:
            model 实例
        """
        if problem_type == 'regression':
            if model_name == 'linear':
                # SGDRegressor - 极快的线性回归
                return SGDRegressor(
                    max_iter=1000,
                    tol=1e-3,
                    random_state=MLService.RANDOM_STATE,
                    early_stopping=True
                )
            else:
                # HistGradientBoostingRegressor - 内存高效的梯度提升
                # 原生支持缺失值，无需额外处理
                return HistGradientBoostingRegressor(
                    max_iter=100,
                    max_depth=5,
                    learning_rate=0.1,
                    random_state=MLService.RANDOM_STATE,
                    early_stopping=True,
                    validation_fraction=0.1
                )
        
        elif problem_type == 'classification':
            if model_name == 'linear':
                # Logistic Regression - 快速且可解释
                return LogisticRegression(
                    max_iter=1000,
                    random_state=MLService.RANDOM_STATE,
                    solver='saga',  # 适合大数据集
                    penalty='l2'
                )
            else:
                # HistGradientBoostingClassifier
                return HistGradientBoostingClassifier(
                    max_iter=100,
                    max_depth=5,
                    learning_rate=0.1,
                    random_state=MLService.RANDOM_STATE,
                    early_stopping=True,
                    validation_fraction=0.1
                )
        
        elif problem_type == 'clustering':
            # MiniBatchKMeans - 比 KMeans 更省内存
            n_clusters = 3  # 默认聚类数
            return MiniBatchKMeans(
                n_clusters=n_clusters,
                random_state=MLService.RANDOM_STATE,
                batch_size=1000,
                max_iter=100
            )
        
        else:
            raise MLServiceError(f"不支持的问题类型: {problem_type}")
    
    @staticmethod
    def train_model(
        df: pd.DataFrame,
        target_col: str,
        problem_type: str,
        model_name: Optional[str] = None,
        n_clusters: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        训练模型 - 完整的 AutoML Pipeline
        
        Week 08 Philosophical Core: ML 自动化模式发现
        Week 14 Implementation Tips: 端到端解决方案
        
        Args:
            df: 数据集
            target_col: 目标列名（clustering 时为 None）
            problem_type: 'regression', 'classification', 或 'clustering'
            model_name: 模型名称（可选，'linear' 或 None）
            n_clusters: 聚类数（仅用于 clustering）
            
        Returns:
            包含模型、指标、特征重要性等的字典
        """
        try:
            start_time = datetime.now()
            logger.info(f"开始训练 {problem_type} 模型...")
            
            # Step 1: 内存优化
            df = MLService._optimize_memory(df.copy())
            gc.collect()  # 手动触发垃圾回收
            
            # Step 2: 科学采样
            if problem_type != 'clustering':
                df_train, was_sampled = MLService._scientific_sampling(
                    df, target_col, problem_type
                )
            else:
                df_train, was_sampled = MLService._scientific_sampling(
                    df, None, problem_type
                )
            
            sampling_warning = None
            if was_sampled:
                sampling_warning = f"已对大数据集进行科学采样，保留 {len(df_train)} 条代表性样本用于训练"
            
            # Step 3: 特征和目标分离
            if problem_type == 'clustering':
                X = df_train.select_dtypes(include=[np.number]).copy()
                y = None
                
                if X.shape[1] == 0:
                    raise MLServiceError("聚类需要至少一个数值特征")
                
                feature_names = X.columns.tolist()
                
            else:
                # 检查目标列是否存在
                if target_col not in df_train.columns:
                    raise MLServiceError(f"目标列 '{target_col}' 不存在于数据集中")
                
                X = df_train.drop(columns=[target_col])
                y = df_train[target_col].copy()
                
                # 检查目标变量缺失值
                if y.isna().any():
                    logger.warning(f"目标列包含 {y.isna().sum()} 个缺失值，将被删除")
                    valid_indices = y.notna()
                    X = X[valid_indices]
                    y = y[valid_indices]
            
            # Step 4: 识别特征类型
            numeric_features = X.select_dtypes(include=[np.number]).columns.tolist()
            categorical_features = X.select_dtypes(include=['object', 'category']).columns.tolist()
            
            logger.info(f"特征统计: {len(numeric_features)} 数值, {len(categorical_features)} 类别")
            
            if len(numeric_features) == 0 and len(categorical_features) == 0:
                raise MLServiceError("没有可用的特征进行训练")
            
            # Step 5: 构建 Pipeline
            if problem_type == 'clustering':
                # 聚类只使用数值特征，不需要复杂 Pipeline
                from sklearn.preprocessing import StandardScaler
                preprocessor = StandardScaler()
                X_processed = preprocessor.fit_transform(X)
                
                # 调整聚类数
                if n_clusters:
                    model = MiniBatchKMeans(
                        n_clusters=n_clusters,
                        random_state=MLService.RANDOM_STATE,
                        batch_size=1000,
                        max_iter=100
                    )
                else:
                    model = MLService._select_model(problem_type, model_name)
                
                # 训练聚类模型
                labels = model.fit_predict(X_processed)
                
                # 评估
                if len(set(labels)) > 1:
                    silhouette_avg = silhouette_score(X_processed, labels)
                    inertia = model.inertia_
                else:
                    silhouette_avg = 0
                    inertia = model.inertia_
                
                metrics = {
                    'silhouette_score': float(silhouette_avg),
                    'inertia': float(inertia),
                    'n_clusters': int(model.n_clusters),
                    'n_samples': int(len(X))
                }
                
                # 保存完整 Pipeline（包含预处理器）
                full_pipeline = {
                    'preprocessor': preprocessor,
                    'model': model,
                    'feature_names': feature_names,
                    'problem_type': problem_type
                }
                
                training_time = (datetime.now() - start_time).total_seconds()
                
                return {
                    'success': True,
                    'pipeline': full_pipeline,
                    'metrics': metrics,
                    'training_samples': len(X),
                    'training_time_seconds': training_time,
                    'warning': sampling_warning,
                    'model_type': 'MiniBatchKMeans'
                }
            
            else:
                # 回归或分类
                preprocessor = MLService._build_preprocessing_pipeline(
                    numeric_features, categorical_features
                )
                
                # 选择模型
                model = MLService._select_model(problem_type, model_name)
                
                # 构建完整 Pipeline (包含特征选择)
                if problem_type == 'regression':
                    # 使用 SelectKBest 或 Lasso 特征选择
                    feature_selector = SelectKBest(score_func=f_regression, k='all')
                else:
                    feature_selector = SelectKBest(score_func=f_classif, k='all')
                
                full_pipeline = Pipeline(steps=[
                    ('preprocessor', preprocessor),
                    ('feature_selector', feature_selector),
                    ('model', model)
                ])
                
                # Step 6: 训练集/测试集划分
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y,
                    test_size=0.2,
                    random_state=MLService.RANDOM_STATE,
                    stratify=y if problem_type == 'classification' else None
                )
                
                logger.info(f"训练集: {len(X_train)} 样本, 测试集: {len(X_test)} 样本")
                
                # Step 7: 训练模型
                full_pipeline.fit(X_train, y_train)
                logger.info("模型训练完成")
                
                gc.collect()  # 训练后清理内存
                
                # Step 8: 严谨评估 - 交叉验证 (Week 08 Implementation Tips)
                logger.info(f"执行 {MLService.CV_FOLDS} 折交叉验证...")
                try:
                    if problem_type == 'regression':
                        cv_scores = cross_val_score(
                            full_pipeline, X_train, y_train,
                            cv=MLService.CV_FOLDS,
                            scoring='r2',
                            n_jobs=1  # GAE 单核
                        )
                    else:
                        cv_scores = cross_val_score(
                            full_pipeline, X_train, y_train,
                            cv=MLService.CV_FOLDS,
                            scoring='accuracy',
                            n_jobs=1
                        )
                    
                    cv_mean = float(np.mean(cv_scores))
                    cv_std = float(np.std(cv_scores))
                    logger.info(f"交叉验证得分: {cv_mean:.4f} (+/- {cv_std:.4f})")
                    
                except Exception as e:
                    logger.warning(f"交叉验证失败: {str(e)}")
                    cv_mean = None
                    cv_std = None
                
                # Step 9: 测试集评估
                y_pred = full_pipeline.predict(X_test)
                
                if problem_type == 'regression':
                    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
                    mae = float(mean_absolute_error(y_test, y_pred))
                    r2 = float(r2_score(y_test, y_pred))
                    
                    metrics = {
                        'rmse': rmse,
                        'mae': mae,
                        'r2': r2,
                        'cv_score': cv_mean,
                        'cv_std': cv_std
                    }
                    logger.info(f"回归指标: RMSE={rmse:.4f}, R²={r2:.4f}, CV={cv_mean:.4f}")
                    
                else:  # classification
                    accuracy = float(accuracy_score(y_test, y_pred))
                    f1 = float(f1_score(y_test, y_pred, average='weighted'))
                    
                    metrics = {
                        'accuracy': accuracy,
                        'f1_weighted': f1,
                        'cv_score': cv_mean,
                        'cv_std': cv_std
                    }
                    logger.info(f"分类指标: Accuracy={accuracy:.4f}, F1={f1:.4f}, CV={cv_mean:.4f}")
                
                # Step 10: 特征重要性（如果模型支持）
                features_importance = MLService._extract_feature_importance(
                    full_pipeline, numeric_features, categorical_features
                )
                
                training_time = (datetime.now() - start_time).total_seconds()
                
                return {
                    'success': True,
                    'pipeline': full_pipeline,
                    'metrics': metrics,
                    'features_importance': features_importance,
                    'training_samples': len(X_train),
                    'test_samples': len(X_test),
                    'training_time_seconds': training_time,
                    'warning': sampling_warning,
                    'model_type': type(model).__name__
                }
        
        except MemoryError as e:
            raise MemoryError(
                "内存不足：数据集过大。请尝试减少数据量或使用更小的数据集。"
            ) from e
        
        except Exception as e:
            logger.error(f"训练模型失败: {str(e)}", exc_info=True)
            raise MLServiceError(f"训练失败: {str(e)}") from e
        
        finally:
            gc.collect()
    
    @staticmethod
    def _extract_feature_importance(
        pipeline: Pipeline,
        numeric_features: List[str],
        categorical_features: List[str]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        提取特征重要性
        
        Week 09 Implementation Tips: 提取特征重要性以提升可解释性
        
        Args:
            pipeline: 训练好的 Pipeline
            numeric_features: 数值特征名
            categorical_features: 类别特征名
            
        Returns:
            特征重要性列表（Top 10）
        """
        try:
            model = pipeline.named_steps['model']
            
            # 检查模型是否有 feature_importances_
            if not hasattr(model, 'feature_importances_'):
                logger.info("模型不支持特征重要性提取")
                return None
            
            # 获取预处理后的特征名
            preprocessor = pipeline.named_steps['preprocessor']
            
            # 获取转换后的特征名
            try:
                feature_names_out = []
                
                # 数值特征（保持原名）
                feature_names_out.extend(numeric_features)
                
                # 类别特征（OneHot 编码后的名称）
                if len(categorical_features) > 0:
                    cat_transformer = preprocessor.named_transformers_['cat']
                    onehot = cat_transformer.named_steps['onehot']
                    cat_feature_names = onehot.get_feature_names_out(categorical_features)
                    feature_names_out.extend(cat_feature_names.tolist())
                
                importances = model.feature_importances_
                
                # 组合特征名和重要性
                feature_importance_dict = dict(zip(feature_names_out, importances))
                
                # 排序并返回 Top 10
                sorted_features = sorted(
                    feature_importance_dict.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
                
                result = [
                    {'feature': name, 'importance': float(importance)}
                    for name, importance in sorted_features
                ]
                
                logger.info(f"提取了 Top {len(result)} 特征重要性")
                return result
                
            except Exception as e:
                logger.warning(f"特征名提取失败: {str(e)}")
                return None
        
        except Exception as e:
            logger.warning(f"特征重要性提取失败: {str(e)}")
            return None
    
    @staticmethod
    def save_model(pipeline: Any, storage_service, uid: str, model_name: str) -> str:
        """
        保存模型到 GCS
        
        Week 14 Implementation Tips: 持久化模型以供后续使用
        
        Args:
            pipeline: 训练好的 Pipeline
            storage_service: StorageService 实例
            uid: 用户 ID
            model_name: 模型名称
            
        Returns:
            GCS 路径
        """
        try:
            # 使用 joblib 压缩保存
            model_buffer = io.BytesIO()
            joblib.dump(pipeline, model_buffer, compress=3)
            model_buffer.seek(0)
            
            # 生成唯一文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"model_{model_name}_{timestamp}.joblib"
            gcs_path = f"models/{uid}/{filename}"
            
            # 上传到 GCS
            full_path = storage_service.upload_file(
                model_buffer,
                gcs_path,
                content_type='application/octet-stream'
            )
            
            logger.info(f"模型已保存至: {full_path}")
            return full_path
            
        except Exception as e:
            logger.error(f"保存模型失败: {str(e)}")
            raise MLServiceError(f"保存模型失败: {str(e)}") from e
    
    @staticmethod
    def load_model(storage_service, gcs_path: str) -> Any:
        """
        从 GCS 加载模型
        
        Args:
            storage_service: StorageService 实例
            gcs_path: GCS 路径（可以是 gs:// 格式或直接路径）
            
        Returns:
            加载的 Pipeline
        """
        try:
            # 处理 gs:// 格式
            if gcs_path.startswith('gs://'):
                # 移除 'gs://bucket_name/'
                parts = gcs_path.replace('gs://', '').split('/', 1)
                if len(parts) == 2:
                    gcs_path = parts[1]
            
            # 从 GCS 下载
            model_bytes = storage_service.download_file(gcs_path)
            model_buffer = io.BytesIO(model_bytes)
            
            # 加载模型
            pipeline = joblib.load(model_buffer)
            
            logger.info(f"成功加载模型: {gcs_path}")
            return pipeline
            
        except Exception as e:
            logger.error(f"加载模型失败: {str(e)}")
            raise MLServiceError(f"加载模型失败: {str(e)}") from e
    
    @staticmethod
    def predict(pipeline: Any, input_data: pd.DataFrame) -> Dict[str, Any]:
        """
        使用模型进行预测
        
        Args:
            pipeline: 训练好的 Pipeline
            input_data: 输入数据（DataFrame）
            
        Returns:
            预测结果字典
        """
        try:
            # 内存优化
            input_data = MLService._optimize_memory(input_data.copy())
            
            # 预测
            predictions = pipeline.predict(input_data)
            
            # 如果是分类且有 predict_proba
            probabilities = None
            if hasattr(pipeline, 'predict_proba'):
                try:
                    probabilities = pipeline.predict_proba(input_data)
                    probabilities = probabilities.tolist()
                except:
                    pass
            
            return {
                'success': True,
                'predictions': predictions.tolist(),
                'probabilities': probabilities,
                'n_samples': len(predictions)
            }
            
        except Exception as e:
            logger.error(f"预测失败: {str(e)}")
            raise MLServiceError(f"预测失败: {str(e)}") from e
