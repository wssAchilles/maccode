"""
机器学习服务模块 - 能源负载预测
ML Service Module for Energy Load Prediction

支持多种模型：RandomForest、LightGBM、XGBoost
自动模型选择和超参数优化
"""

import pandas as pd
import numpy as np
import joblib
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Union, Any
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor, VotingRegressor
from sklearn.model_selection import train_test_split, TimeSeriesSplit, RandomizedSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings

warnings.filterwarnings('ignore')

# 可选依赖：LightGBM 和 XGBoost
try:
    from lightgbm import LGBMRegressor
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    print("⚠️ LightGBM 未安装，将使用 RandomForest")

try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("⚠️ XGBoost 未安装，将使用 RandomForest")


from config import Config

class MLServiceError(Exception):
    """ML Service Generic Error"""
    pass

class MemoryError(Exception):
    """Memory Limit Exceeded"""
    pass


class EnergyPredictor:
    """
    能源负载预测器
    
    使用随机森林模型预测未来24小时的能源负载
    支持模型训练、保存、加载和推理
    """
    
    def __init__(self, model_path: str = None):
        """
        初始化预测器
        
        Args:
            model_path: 本地兜底模型路径（可选），主要从 Firebase Storage 加载
        """
        # 获取项目根目录
        self.script_dir = Path(__file__).parent  # services 目录
        self.back_dir = self.script_dir.parent  # back 目录
        
        # Firebase Storage 模型路径（主要存储位置）
        self.firebase_model_path = 'models/rf_model.joblib'
        
        # 本地兜底模型路径（部署包中自带的模型，仅用于首次加载）
        if model_path:
            self.local_model_path = Path(model_path)
        else:
            self.local_model_path = self.back_dir / 'models' / 'rf_model.joblib'
        
        # 初始化 StorageService
        from services.storage_service import StorageService
        self.storage_service = StorageService()
        
        # 初始化模型
        self.model: Optional[RandomForestRegressor] = None
        
        # 基础特征列表（向后兼容）
        self.base_feature_columns = [
            'Hour', 'DayOfWeek', 'Temperature', 'Price',
            'Lag_1h', 'Lag_24h', 'Lag_168h',
            'Rolling_Mean_6h', 'Rolling_Std_6h', 'Rolling_Mean_24h',
            'Temp_x_Hour', 'Lag24_x_DayOfWeek'
        ]
        
        # 增强特征列表（新增的时间特征）
        self.enhanced_feature_columns = [
            # 基础时间特征
            'Month', 'Season', 'IsWeekend', 'IsHoliday', 'DayOfMonth', 'WeekOfYear',
            # 增强交互特征
            'Temp_x_Season', 'Lag24_x_IsWeekend', 'Hour_x_IsHoliday',
            # 周期编码特征
            'Month_Sin', 'Month_Cos', 'Hour_Sin', 'Hour_Cos',
            # 分位数与波动率特征 (Phase 1 新增)
            'Quantile_95_24h', 'Quantile_05_24h', 'Volatility_24h',
            'Price_Change', 'Load_Change_1h', 'Load_Change_Pct_1h'
        ]
        
        # 实际使用的特征列表（初始化为基础特征）
        self.feature_columns = self.base_feature_columns.copy()
        self.target_column = 'Site_Load'
        
        print(f"📁 Firebase Storage 模型路径: {self.firebase_model_path}")
        print(f"📁 本地兜底模型路径: {self.local_model_path}")
    
    def _load_feature_columns_from_metadata(self):
        """
        从模型元数据中加载特征列表
        确保预测时使用与训练时相同的特征
        """
        try:
            metadata = self.get_model_metadata()
            if metadata and 'feature_engineering' in metadata:
                fe_info = metadata['feature_engineering']
                if fe_info.get('use_enhanced', False):
                    # 模型使用了增强特征，更新特征列表
                    enhanced_list = fe_info.get('enhanced_features_list', [])
                    if enhanced_list:
                        self.feature_columns = self.base_feature_columns.copy()
                        self.feature_columns.extend(enhanced_list)
                        print(f"   ✓ 已从元数据恢复特征列表: {len(self.feature_columns)} 个特征")
                        print(f"     (基础: {len(self.base_feature_columns)}, 增强: {len(enhanced_list)})")
                else:
                    # 模型只使用基础特征
                    self.feature_columns = self.base_feature_columns.copy()
                    print(f"   ✓ 模型使用基础特征: {len(self.feature_columns)} 个")
            else:
                print(f"   ⚠️  未找到特征元数据，使用默认基础特征")
                
            # 加载训练配置 (Log Transform)
            if metadata and 'training_config' in metadata:
                config = metadata['training_config']
                self.use_log_transform = config.get('use_log_transform', False)
                if self.use_log_transform:
                    print(f"   ✓ 模型使用 Log1p 变换，预测时将自动还原")
            else:
                self.use_log_transform = False
                
        except Exception as e:
            print(f"   ⚠️  加载特征元数据失败: {e}，使用默认基础特征")
            self.use_log_transform = False
    
    def _get_model_type_name(self) -> str:
        """获取当前模型的类型名称"""
        if self.model is None:
            return 'Unknown'
        
        model_class = type(self.model).__name__
        name_map = {
            'RandomForestRegressor': 'Random Forest Regressor',
            'LGBMRegressor': 'LightGBM Regressor',
            'XGBRegressor': 'XGBoost Regressor'
        }
        return name_map.get(model_class, model_class)
    
    def _create_model(self, model_type: str, n_estimators: int = 100, random_state: int = 42):
        """
        创建指定类型的模型
        
        Args:
            model_type: 模型类型 ('randomforest', 'lightgbm', 'xgboost')
            n_estimators: 树的数量
            random_state: 随机种子
            
        Returns:
            (model, hyperparameters) 元组
        """
        model_type = model_type.lower()
        
        if model_type == 'lightgbm' and LIGHTGBM_AVAILABLE:
            model = LGBMRegressor(
                n_estimators=n_estimators,
                learning_rate=0.05,
                max_depth=15,
                num_leaves=31,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=random_state,
                n_jobs=-1,
                verbose=-1
            )
            params = {
                'n_estimators': n_estimators,
                'learning_rate': 0.05,
                'max_depth': 15,
                'num_leaves': 31
            }
        elif model_type == 'xgboost' and XGBOOST_AVAILABLE:
            model = XGBRegressor(
                n_estimators=n_estimators,
                learning_rate=0.05,
                max_depth=10,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=random_state,
                n_jobs=-1,
                verbosity=0
            )
            params = {
                'n_estimators': n_estimators,
                'learning_rate': 0.05,
                'max_depth': 10
            }
        # ================================================================
        # 新增: 线性基线模型 (Linear Baselines for Interpretability)
        # ================================================================
        elif model_type == 'ridge':
            from sklearn.linear_model import Ridge
            from sklearn.preprocessing import StandardScaler
            from sklearn.pipeline import Pipeline
            # 使用 Pipeline 确保特征标准化 (线性模型对尺度敏感)
            model = Pipeline([
                ('scaler', StandardScaler()),
                ('ridge', Ridge(alpha=1.0, random_state=random_state))
            ])
            params = {
                'alpha': 1.0,
                'model_type': 'Ridge (L2 Regularization)'
            }
        elif model_type == 'lasso':
            from sklearn.linear_model import Lasso
            from sklearn.preprocessing import StandardScaler
            from sklearn.pipeline import Pipeline
            model = Pipeline([
                ('scaler', StandardScaler()),
                ('lasso', Lasso(alpha=0.1, random_state=random_state, max_iter=2000))
            ])
            params = {
                'alpha': 0.1,
                'model_type': 'Lasso (L1 Regularization)'
            }
        elif model_type == 'elasticnet':
            from sklearn.linear_model import ElasticNet
            from sklearn.preprocessing import StandardScaler
            from sklearn.pipeline import Pipeline
            model = Pipeline([
                ('scaler', StandardScaler()),
                ('elasticnet', ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=random_state, max_iter=2000))
            ])
            params = {
                'alpha': 0.1,
                'l1_ratio': 0.5,
                'model_type': 'ElasticNet (L1+L2 Regularization)'
            }
        # ================================================================
        else:
            # 默认使用 RandomForest
            model = RandomForestRegressor(
                n_estimators=n_estimators,
                max_depth=20,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=random_state,
                n_jobs=-1,
                verbose=0
            )
            params = {
                'n_estimators': n_estimators,
                'max_depth': 20,
                'min_samples_split': 5,
                'min_samples_leaf': 2
            }
        
        return model, params
    
    def _tune_model(self, model_type: str, X_train, y_train, cv_split, n_iter: int = 20, random_state: int = 42):
        """
        使用 Optuna 对指定模型进行贝叶斯超参数调优 (Phase 1 改进)
        
        优势:
        - 贝叶斯优化比随机搜索更高效
        - MedianPruner 提前终止表现差的 trial
        - 自动保存调参日志 (tuning_log.csv)
        """
        try:
            import optuna
            from optuna.pruners import MedianPruner
            from sklearn.model_selection import cross_val_score
            optuna.logging.set_verbosity(optuna.logging.WARNING)
            OPTUNA_AVAILABLE = True
        except ImportError:
            OPTUNA_AVAILABLE = False
            print("   ⚠️ Optuna 未安装，回退到 RandomizedSearchCV")
        
        model_type = model_type.lower()
        
        # 如果 Optuna 不可用，使用原有的 RandomizedSearchCV
        if not OPTUNA_AVAILABLE:
            return self._tune_model_fallback(model_type, X_train, y_train, cv_split, n_iter, random_state)
        
        print(f"   🔍 使用 Optuna 为 {model_type} 搜索最佳参数 (trials={n_iter})...")
        
        def objective(trial):
            """Optuna 目标函数"""
            if model_type == 'lightgbm' and LIGHTGBM_AVAILABLE:
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 100, 500),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.15, log=True),
                    'num_leaves': trial.suggest_int('num_leaves', 20, 150),
                    'max_depth': trial.suggest_int('max_depth', 5, 25),
                    'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                    'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                    'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
                    'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
                }
                model = LGBMRegressor(**params, random_state=random_state, n_jobs=-1, verbose=-1)
                
            elif model_type == 'xgboost' and XGBOOST_AVAILABLE:
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 100, 500),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.15, log=True),
                    'max_depth': trial.suggest_int('max_depth', 3, 15),
                    'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                    'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                    'gamma': trial.suggest_float('gamma', 0, 0.5),
                    'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
                    'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
                }
                model = XGBRegressor(**params, random_state=random_state, n_jobs=-1, verbosity=0)
                
            else:
                # RandomForest
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 100, 400),
                    'max_depth': trial.suggest_int('max_depth', 5, 30),
                    'min_samples_split': trial.suggest_int('min_samples_split', 2, 15),
                    'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 8),
                    'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2', None]),
                }
                model = RandomForestRegressor(**params, random_state=random_state, n_jobs=-1)
            
            # 使用交叉验证评估
            scores = cross_val_score(
                model, X_train, y_train, 
                cv=cv_split, 
                scoring='neg_mean_absolute_error',
                n_jobs=-1
            )
            
            return -scores.mean()  # Optuna 默认最小化，负 MAE 的均值
        
        # 创建 Optuna Study
        study = optuna.create_study(
            direction='minimize',
            pruner=MedianPruner(n_startup_trials=5, n_warmup_steps=0),
            sampler=optuna.samplers.TPESampler(seed=random_state)
        )
        
        # 运行优化
        study.optimize(
            objective, 
            n_trials=n_iter, 
            show_progress_bar=False,
            n_jobs=1  # 避免嵌套并行
        )
        
        # 保存调参日志
        try:
            log_df = study.trials_dataframe()
            log_path = 'tuning_log.csv'
            log_df.to_csv(log_path, index=False)
            print(f"      📝 调参日志已保存: {log_path}")
        except Exception as e:
            print(f"      ⚠️ 保存调参日志失败: {e}")
        
        # 使用最佳参数重新训练模型
        best_params = study.best_params
        print(f"      ✓ 最佳参数: {best_params}")
        print(f"      ✓ 最佳 CV MAE: {study.best_value:.4f} kW")
        
        # 创建最终模型
        if model_type == 'lightgbm' and LIGHTGBM_AVAILABLE:
            best_model = LGBMRegressor(**best_params, random_state=random_state, n_jobs=-1, verbose=-1)
        elif model_type == 'xgboost' and XGBOOST_AVAILABLE:
            best_model = XGBRegressor(**best_params, random_state=random_state, n_jobs=-1, verbosity=0)
        else:
            best_model = RandomForestRegressor(**best_params, random_state=random_state, n_jobs=-1)
        
        # 在完整训练集上训练
        best_model.fit(X_train, y_train)
        
        return best_model, best_params
    
    def _tune_model_fallback(self, model_type: str, X_train, y_train, cv_split, n_iter: int = 20, random_state: int = 42):
        """
        Fallback: 使用 RandomizedSearchCV 进行超参数调优 (当 Optuna 不可用时)
        """
        model_type = model_type.lower()
        estimator = None
        param_dist = {}
        
        if model_type == 'lightgbm' and LIGHTGBM_AVAILABLE:
            estimator = LGBMRegressor(random_state=random_state, n_jobs=-1, verbose=-1)
            param_dist = {
                'n_estimators': [100, 200, 300, 500],
                'learning_rate': [0.01, 0.03, 0.05, 0.1],
                'num_leaves': [31, 50, 70, 100],
                'max_depth': [10, 15, 20, -1],
                'subsample': [0.7, 0.8, 0.9],
                'colsample_bytree': [0.7, 0.8, 0.9]
            }
        elif model_type == 'xgboost' and XGBOOST_AVAILABLE:
            estimator = XGBRegressor(random_state=random_state, n_jobs=-1, verbosity=0)
            param_dist = {
                'n_estimators': [100, 200, 300, 500],
                'learning_rate': [0.01, 0.03, 0.05, 0.1],
                'max_depth': [3, 6, 10, 15],
                'subsample': [0.7, 0.8, 0.9],
                'colsample_bytree': [0.7, 0.8, 0.9],
                'gamma': [0, 0.1, 0.2]
            }
        else:
            estimator = RandomForestRegressor(random_state=random_state, n_jobs=-1)
            param_dist = {
                'n_estimators': [100, 200, 300],
                'max_depth': [10, 20, 30, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4],
                'max_features': ['sqrt', 'log2', None]
            }
            
        print(f"   🔍 使用 RandomizedSearchCV 为 {model_type} 搜索最佳参数 (iter={n_iter})...")
        
        search = RandomizedSearchCV(
            estimator=estimator,
            param_distributions=param_dist,
            n_iter=n_iter,
            cv=cv_split,
            scoring='neg_mean_absolute_error',
            random_state=random_state,
            n_jobs=-1,
            verbose=0
        )
        
        search.fit(X_train, y_train)
        print(f"      ✓ 最佳参数: {search.best_params_}")
        return search.best_estimator_, search.best_params_

    def _auto_select_best_model(
        self, 
        X_train, y_train, 
        X_test, y_test, 
        random_state: int = 42,
        use_time_series_cv: bool = True,
        n_splits: int = 5,
        perform_tuning: bool = True  # 新增参数
    ) -> tuple:
        """
        自动选择最佳模型（支持时间序列交叉验证）
        
        比较多种模型配置，选择测试集 MAE 最低的
        
        Args:
            X_train, y_train: 训练数据
            X_test, y_test: 测试数据
            random_state: 随机种子
            use_time_series_cv: 是否使用时间序列交叉验证（默认 True）
            n_splits: 交叉验证折数（默认 5）
            
        Returns:
            (best_model, best_params, selection_info) 元组
        """
        candidates = []
        results = {}
        cv_details = {}
        
        if perform_tuning:
            # 如果启用调优，此时我们不使用预设的配置，而是针对每个模型类型运行搜索
            # 但为了保持代码结构，我们构建一个待调优类型列表
            # 这里的 (DisplayName, type, init_n_estimators) 仅用于元组解包，n_estimators 会被忽略
            tuning_targets = [('RandomForest', 'randomforest', 100)]
            if LIGHTGBM_AVAILABLE:
                tuning_targets.append(('LightGBM', 'lightgbm', 100))
            if XGBOOST_AVAILABLE:
                tuning_targets.append(('XGBoost', 'xgboost', 100))
            
            model_configs = tuning_targets # 替换为调优目标
        else:
            # 原有的固定配置模式
            model_configs = [
                ('RandomForest', 'randomforest', 150),
                ('RandomForest_200', 'randomforest', 200),
            ]
            
            # 如果 LightGBM 可用，添加到候选
            if LIGHTGBM_AVAILABLE:
                model_configs.extend([
                    ('LightGBM', 'lightgbm', 200),
                    ('LightGBM_300', 'lightgbm', 300),
                ])
            
            # 如果 XGBoost 可用，添加到候选
            if XGBOOST_AVAILABLE:
                model_configs.extend([
                    ('XGBoost', 'xgboost', 200),
                    ('XGBoost_300', 'xgboost', 300),
                ])
        
        print(f"   评估 {len(model_configs)} 种模型配置...")
        if use_time_series_cv:
            print(f"   📊 使用 TimeSeriesSplit 交叉验证 ({n_splits} 折)")
        
        baseline_mae = None
        best_mae = float('inf')
        best_model = None
        best_params = None
        best_name = None
        
        # 【修复】时间序列交叉验证只在训练集上进行，测试集保持独立用于最终评估
        # 这避免了测试集参与模型选择导致的数据泄漏
        if use_time_series_cv:
            # CV 只在训练集上做，不再把测试集拼进去
            tscv = TimeSeriesSplit(n_splits=n_splits)
            print(f"   📊 TimeSeriesSplit CV 仅在训练集上进行 ({len(X_train)} 样本)")
        
        # 存储每种类型的最佳模型，用于集成
        best_estimators = {}
        
        for name, model_type, n_estimators in model_configs:
            try:
                model = None
                params = None
                
                if perform_tuning:
                    # 使用超参数搜索
                    # 注意：复用 tscv 作为 cv_split
                    # 如果未启用 TimeSeriesCV，则使用 KFold 或者默认的 5折
                    cv_to_use = tscv if use_time_series_cv else 5
                    
                    # 调优后的名字加上 "Tuned" 后缀
                    name = f"{name}_Tuned"
                    model, params = self._tune_model(model_type, X_train, y_train, cv_to_use, n_iter=15, random_state=random_state)
                else:
                    # 使用固定配置
                    print(f"   - 训练 {name}...", end=' ')
                    model, params = self._create_model(model_type, n_estimators, random_state)
                
                if use_time_series_cv:
                    # 【修复】时间序列交叉验证只在训练集上进行
                    cv_scores = []
                    for train_idx, val_idx in tscv.split(X_train):
                        X_cv_train, X_cv_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
                        y_cv_train, y_cv_val = y_train.iloc[train_idx], y_train.iloc[val_idx]
                        
                        model_cv, _ = self._create_model(model_type, n_estimators, random_state)
                        model_cv.fit(X_cv_train, y_cv_train)
                        y_cv_pred = model_cv.predict(X_cv_val)
                        
                        # 如果启用了对数变换，需要还原预测值
                        if hasattr(self, 'use_log_transform') and self.use_log_transform:
                            y_cv_val = np.expm1(y_cv_val)
                            y_cv_pred = np.expm1(y_cv_pred)
                            
                        cv_scores.append(mean_absolute_error(y_cv_val, y_cv_pred))
                    
                    # 计算交叉验证平均分
                    cv_mae = np.mean(cv_scores)
                    cv_std = np.std(cv_scores)
                    
                    # 使用完整训练数据重新训练最终模型
                    model.fit(X_train, y_train)
                    
                    # 在独立的未来测试集上评估（严格未见数据）
                    y_pred = model.predict(X_test)
                    
                    # 如果启用了对数变换，需要还原预测值
                    if hasattr(self, 'use_log_transform') and self.use_log_transform:
                         # y_test 是原始值（如果不改动 y_test 的话），这里需要确认 split 时 y_test 是否被 log
                         # 我们的策略是：只对训练集的 y 进行 log，测试集的 y 保持原样或者反变换
                         # 为统一处理，假设 fit 时 y_train 是 log 后的，predict 输出 log 后的
                         y_pred = np.expm1(y_pred)
                         # y_test 在 split 前如果没变，那就是原始值。
                         # 为了安全，我们稍后在 split 处做处理。
                    
                    test_mae = mean_absolute_error(y_test, y_pred)
                    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                    
                    # 使用交叉验证 MAE 作为选择依据（更可靠）
                    mae = cv_mae
                    rmse = test_rmse
                    
                    cv_details[name] = {
                        'cv_mae_mean': round(cv_mae, 2),
                        'cv_mae_std': round(cv_std, 2),
                        'cv_scores': [round(s, 2) for s in cv_scores],
                        'test_mae': round(test_mae, 2)  # 记录独立测试集的 MAE
                    }
                    
                    print(f"CV_MAE={cv_mae:.2f}±{cv_std:.2f} kW, Test_MAE={test_mae:.2f} kW (独立未来数据)")
                else:
                    # 原有的简单训练-测试拆分
                    model.fit(X_train, y_train)
                    y_pred = model.predict(X_test)
                    
                    if hasattr(self, 'use_log_transform') and self.use_log_transform:
                        y_pred = np.expm1(y_pred)
                    
                    mae = mean_absolute_error(y_test, y_pred)
                    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                    print(f"MAE={mae:.2f} kW")
                
                results[name] = {'mae': mae, 'rmse': rmse, 'model_type': model_type}
                candidates.append(name)
                
                # 记录基准（第一个 RandomForest）
                if baseline_mae is None:
                    baseline_mae = mae
                
                # 更新最佳
                if mae < best_mae:
                    best_mae = mae
                    best_model = model
                    best_params = params
                    best_name = name
                    
            except Exception as e:
                print(f"失败: {str(e)}")
                continue
            
            # 记录该类型的最佳模型用于集成
            if model_type not in best_estimators or mae < best_estimators[model_type]['mae']:
                best_estimators[model_type] = {
                    'model': model,
                    'mae': mae
                }
        
        # 尝试集成学习 (VotingRegressor)
        if len(best_estimators) >= 2:
            try:
                print(f"   🤝 尝试集成学习 (VotingRegressor)...", end=' ')
                # 创建 VotingRegressor
                estimators_list = [(k, v['model']) for k, v in best_estimators.items()]
                voting_model = VotingRegressor(estimators=estimators_list, n_jobs=-1)
                voting_name = "Voting_Ensemble"
                
                # 评估 Voting 模型
                if use_time_series_cv:
                    cv_scores = []
                    for train_idx, val_idx in tscv.split(X_train):
                        X_cv_train, X_cv_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
                        y_cv_train, y_cv_val = y_train.iloc[train_idx], y_train.iloc[val_idx]
                        
                        from sklearn.base import clone
                        model_cv = clone(voting_model)
                        model_cv.fit(X_cv_train, y_cv_train)
                        y_cv_pred = model_cv.predict(X_cv_val)
                        cv_scores.append(mean_absolute_error(y_cv_val, y_cv_pred))
                    
                    cv_mae = np.mean(cv_scores)
                    cv_std = np.std(cv_scores)
                    
                    voting_model.fit(X_train, y_train)
                    y_pred = voting_model.predict(X_test)
                    
                    if hasattr(self, 'use_log_transform') and self.use_log_transform:
                         y_pred = np.expm1(y_pred)
                         
                    test_mae = mean_absolute_error(y_test, y_pred)
                    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                    
                    mae = cv_mae
                    rmse = test_rmse
                    
                    cv_details[voting_name] = {
                        'cv_mae_mean': round(cv_mae, 2),
                        'cv_mae_std': round(cv_std, 2),
                        'cv_scores': [round(s, 2) for s in cv_scores],
                        'test_mae': round(test_mae, 2)
                    }
                    print(f"CV_MAE={cv_mae:.2f}±{cv_std:.2f} kW, Test_MAE={test_mae:.2f} kW")
                else:
                    voting_model.fit(X_train, y_train)
                    y_pred = voting_model.predict(X_test)
                    
                    if hasattr(self, 'use_log_transform') and self.use_log_transform:
                        y_pred = np.expm1(y_pred)
                    
                    mae = mean_absolute_error(y_test, y_pred)
                    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                    print(f"MAE={mae:.2f} kW")
                
                results[voting_name] = {'mae': mae, 'rmse': rmse, 'model_type': 'voting'}
                candidates.append(voting_name)
                
                if mae < best_mae:
                    best_mae = mae
                    best_model = voting_model
                    best_params = {'estimators': [k for k in best_estimators.keys()]}
                    best_name = voting_name
                    print(f"   ✨ 集成模型表现最佳!")
                    
            except Exception as e:
                print(f"   ⚠️ Voting 集成学习失败: {str(e)}")
        
        # ================================================================
        # 新增: StackingRegressor 集成 (使用 RidgeCV 作为 Meta-Learner)
        # ================================================================
        if len(best_estimators) >= 2:
            try:
                from sklearn.ensemble import StackingRegressor
                from sklearn.linear_model import RidgeCV
                
                print(f"   🏗️  尝试 Stacking 集成 (Meta-Learner: RidgeCV)...", end=' ')
                
                # 创建 StackingRegressor
                stacking_estimators = [(k, v['model']) for k, v in best_estimators.items()]
                stacking_model = StackingRegressor(
                    estimators=stacking_estimators,
                    final_estimator=RidgeCV(alphas=[0.1, 1.0, 10.0]),
                    cv=5,
                    n_jobs=-1,
                    passthrough=False  # 不传递原始特征给 Meta-Learner
                )
                stacking_name = "Stacking_Ensemble"
                
                # 评估 Stacking 模型
                stacking_model.fit(X_train, y_train)
                y_pred = stacking_model.predict(X_test)
                
                if hasattr(self, 'use_log_transform') and self.use_log_transform:
                    y_pred = np.expm1(y_pred)
                
                mae = mean_absolute_error(y_test, y_pred)
                rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                print(f"MAE={mae:.2f} kW")
                
                results[stacking_name] = {'mae': mae, 'rmse': rmse, 'model_type': 'stacking'}
                candidates.append(stacking_name)
                
                if mae < best_mae:
                    best_mae = mae
                    best_model = stacking_model
                    best_params = {
                        'estimators': [k for k in best_estimators.keys()],
                        'final_estimator': 'RidgeCV'
                    }
                    best_name = stacking_name
                    print(f"   ✨ Stacking 模型表现最佳!")
                    
            except Exception as e:
                print(f"   ⚠️ Stacking 集成失败: {str(e)}")

        # 计算相对基准的提升
        improvement = 'N/A'
        if baseline_mae and baseline_mae > 0:
            improvement_pct = (baseline_mae - best_mae) / baseline_mae * 100
            improvement = f"{improvement_pct:.1f}%"
        
        print(f"\n   🏆 最佳模型: {best_name} (MAE={best_mae:.2f} kW)")
        if improvement != 'N/A' and improvement != '0.0%':
            print(f"   📈 相比基准提升: {improvement}")
        
        selection_info = {
            'winner': best_name,
            'candidates_evaluated': candidates,
            'all_scores': {k: {'mae': round(v['mae'], 2), 'rmse': round(v['rmse'], 2)} 
                          for k, v in results.items()},
            'improvement': improvement,
            'validation_method': 'TimeSeriesSplit' if use_time_series_cv else 'HoldOut',
            'cv_folds': n_splits if use_time_series_cv else None,
            'cv_details': cv_details if use_time_series_cv else None
        }
        
        return best_model, best_params, selection_info
    
    def _get_price(self, hour: int) -> float:
        """
        根据小时返回峰谷电价 (从配置读取)
        
        Args:
            hour: 小时 (0-23)
            
        Returns:
            电价 (元/kWh)
        """
        schedule = Config.PRICE_SCHEDULE
        
        if hour in schedule['peak_hours_list']:
            return schedule['peak']
        elif hour in schedule['normal_hours_list']:
            return schedule['normal']
        else:
            return schedule['valley']
    
    def _save_model_metadata(self, metadata: dict) -> bool:
        """
        保存模型元数据到 Firebase Storage (JSON 文件)
        
        Args:
            metadata: 模型元数据字典
            
        Returns:
            是否保存成功
        """
        try:
            import json
            from datetime import datetime
            
            # 添加更新时间戳
            metadata['updated_at'] = datetime.now().isoformat()
            
            # 转换为 JSON 字符串
            json_data = json.dumps(metadata, indent=2, ensure_ascii=False)
            
            # 上传到 Storage (使用临时文件确保 Content-Type 正确)
            import tempfile
            metadata_path = 'models/model_metadata.json'
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                f.write(json_data)
                temp_path = f.name
            
            try:
                with open(temp_path, 'rb') as f:
                    self.storage_service.bucket.blob(metadata_path).upload_from_file(
                        f, 
                        content_type='application/json'
                    )
            finally:
                import os
                os.unlink(temp_path)
            
            print(f"   ✓ 模型元数据已保存到 Firebase Storage: {metadata_path}")
            return True
            
        except Exception as e:
            print(f"   ❌ 保存模型元数据失败: {str(e)}")
            return False
    
    @staticmethod
    def get_model_metadata() -> Optional[dict]:
        """
        从 Firebase Storage 获取模型元数据 (JSON 文件)
        
        Returns:
            模型元数据字典，如果不存在返回 None
        """
        try:
            import json
            from services.storage_service import StorageService
            
            # 创建 Storage 服务实例
            storage = StorageService()
            
            # 下载元数据 JSON
            metadata_path = 'models/model_metadata.json'
            json_bytes = storage.download_file(metadata_path)
            
            # 解析 JSON
            metadata = json.loads(json_bytes.decode('utf-8'))
            return metadata
                
        except Exception as e:
            print(f"获取模型元数据失败: {str(e)}")
            return None
    
    def _is_gae_environment(self) -> bool:
        """检测是否在 GAE 环境"""
        return bool(os.getenv('GAE_ENV') or os.getenv('K_SERVICE'))

    def train_model(
        self, 
        data_path: str = None,
        n_estimators: int = 100,
        test_size: float = 0.2,
        random_state: int = 42,
        use_firebase_storage: bool = True,
        auto_select_model: bool = True,
        model_type: str = 'auto',
        use_enhanced_features: bool = True,
        use_time_series_cv: bool = True,
        cv_folds: int = 5,
        use_log_transform: bool = True,
        remove_outliers: bool = True,
        tune_hyperparameters: bool = True,
        target_col: str = 'Site_Load'  # Allow custom target column
    ) -> Dict[str, float]:
        """
        训练预测模型（支持自动模型选择、增强特征和时间序列交叉验证）
        
        Args:
            data_path: 数据文件路径
            n_estimators: 树的数量
            test_size: 测试集比例
            random_state: 随机种子
            use_firebase_storage: 是否从 Firebase Storage 下载数据
            auto_select_model: 是否自动选择最佳模型
            model_type: 指定模型类型
            use_enhanced_features: 是否使用增强特征
            use_time_series_cv: 是否使用时间序列交叉验证
            cv_folds: 交叉验证折数
            use_log_transform: 是否对目标变量进行 Log1p 变换 (默认 True)
            remove_outliers: 是否自动过滤异常值 (默认 True)
            tune_hyperparameters: 是否启用超参数自动搜索 (默认 True) 
            
        Returns:
            包含评估指标的字典
        """
        print("\n" + "="*80)
        print("🚀 开始训练能源负载预测模型")
        print("="*80 + "\n")
        
        # Set target column
        self.target_column = target_col
        print(f"   🎯 目标列: {self.target_column}")
        
        temp_data_path = None
        
        try:
            # 从 Firebase Storage 下载数据
            if use_firebase_storage:
                print("📥 从 Firebase Storage 下载训练数据...")
                from services.storage_service import StorageService
                
                storage_service = StorageService()
                firebase_path = data_path or 'data/processed/cleaned_energy_data_all.csv'
                
                temp_data_path = storage_service.download_to_temp(firebase_path)
                
                if temp_data_path is None:
                    raise FileNotFoundError(f"无法从 Firebase Storage 下载数据: {firebase_path}")
                
                data_path = temp_data_path
                print(f"   ✓ 数据已下载到: {data_path}")
            else:
                # 本地文件模式 (开发环境)
                if data_path is None:
                    # 尝试多个可能的路径
                    possible_paths = [
                        self.back_dir.parent / 'data' / 'processed' / 'cleaned_energy_data_all.csv',
                        self.back_dir / 'data' / 'processed' / 'cleaned_energy_data_all.csv',
                    ]
                    data_path = None
                    for path in possible_paths:
                        if path.exists():
                            data_path = path
                            break
                    if data_path is None:
                        data_path = possible_paths[0]  # 使用第一个作为默认
                else:
                    data_path = Path(data_path)
            
            # 读取数据
            print(f"📖 读取数据: {data_path}")
            try:
                df = pd.read_csv(data_path, parse_dates=['Date'])
                print(f"   ✓ 数据读取成功: {len(df)} 行 × {len(df.columns)} 列")
            except FileNotFoundError:
                raise FileNotFoundError(f"数据文件不存在: {data_path}")
            except Exception as e:
                raise Exception(f"读取数据时出错: {str(e)}")
            
            # ================================================================
            # 【修复】智能特征检查与自动补算
            # 分层检查：硬必需列 vs 可补算的 engineered 特征
            # ================================================================
            
            # 硬必需列：必须存在，无法自动生成
            hard_required = ['Date', 'Site_Load', 'Temperature']
            missing_hard = [col for col in hard_required if col not in df.columns]
            if missing_hard:
                raise ValueError(f"数据缺少核心必需列（无法自动生成）: {missing_hard}")
            
            # 可补算的基础时间特征
            time_features = ['Hour', 'DayOfWeek', 'Price']
            missing_time = [col for col in time_features if col not in df.columns]
            
            # 可补算的 Lag/Rolling 特征
            engineered_features = ['Lag_1h', 'Lag_24h', 'Lag_168h', 
                                   'Rolling_Mean_6h', 'Rolling_Std_6h', 'Rolling_Mean_24h',
                                   'Temp_x_Hour', 'Lag24_x_DayOfWeek']
            missing_engineered = [col for col in engineered_features if col not in df.columns]
            
            # 检查增强特征是否缺失
            missing_enhanced_time = []
            if use_enhanced_features:
                 enhanced_time_cols = ['Month', 'Season', 'IsWeekend', 'IsHoliday']
                 missing_enhanced_time = [c for c in enhanced_time_cols if c not in df.columns]

            # 如果有缺失的可补算特征，自动调用 EnergyDataProcessor 补算
            if missing_time or missing_engineered or missing_enhanced_time:
                print(f"\n🔧 检测到缺失特征，自动补算中...")
                if missing_time:
                    print(f"   - 缺失时间特征: {missing_time}")
                if missing_engineered:
                    print(f"   - 缺失工程特征: {missing_engineered}")
                
                from services.data_processor import EnergyDataProcessor
                processor = EnergyDataProcessor()
                
                # 确保 Date 是 datetime 类型
                if df['Date'].dtype == 'object':
                    df['Date'] = pd.to_datetime(df['Date'])
                
                # 补算时间特征
                if missing_time:
                    if 'Hour' not in df.columns:
                        df['Hour'] = df['Date'].dt.hour
                    if 'DayOfWeek' not in df.columns:
                        df['DayOfWeek'] = df['Date'].dt.dayofweek
                    if 'Price' not in df.columns:
                        df = processor.add_price_feature(df)
                
                # 补算增强时间特征（如果启用）
                if use_enhanced_features:
                    enhanced_time_cols = ['Month', 'Season', 'IsWeekend', 'IsHoliday']
                    missing_enhanced_time = [c for c in enhanced_time_cols if c not in df.columns]
                    if missing_enhanced_time:
                        df = processor.add_enhanced_time_features(df)
                        print(f"   ✓ 已补算增强时间特征")
                
                # 补算 Lag/Rolling/Interaction 特征
                if missing_engineered:
                    df = processor.add_advanced_features(df, dropna=False, use_enhanced=use_enhanced_features)
                    print(f"   ✓ 已补算 Lag/Rolling/Interaction 特征")
                
                print(f"   ✓ 特征补算完成，当前列数: {len(df.columns)}")
            
            # 处理缺失值
            print(f"\n🔍 检查数据质量...")
            # 检查核心列的缺失值
            core_cols = hard_required + time_features
            null_counts = df[core_cols].isnull().sum()
            if null_counts.sum() > 0:
                print(f"   ⚠️  发现缺失值:")
                for col, count in null_counts[null_counts > 0].items():
                    print(f"      - {col}: {count} 个")
                
                # 对于 Temperature，使用均值填充
                if 'Temperature' in null_counts and null_counts['Temperature'] > 0:
                    # 使用线性插值填充温度缺失值（更适合时间序列）
                    df['Temperature'] = df['Temperature'].interpolate(method='linear', limit_direction='both')
                    # 如果仍有缺失（例如开头或结尾），使用均值兜底
                    if df['Temperature'].isnull().sum() > 0:
                         df['Temperature'].fillna(df['Temperature'].mean(), inplace=True)
                    print(f"   ✓ Temperature 缺失值已使用线性插值填充")
            else:
                print(f"   ✓ 无核心列缺失值")
            
            # ================================================================
            # 动态特征选择（检测数据中可用的增强特征）
            # ================================================================
            print(f"\n🔧 检测可用特征...")
            
            # 首先使用基础特征
            available_features = [col for col in self.base_feature_columns if col in df.columns]
            print(f"   ✓ 基础特征: {len(available_features)}/{len(self.base_feature_columns)}")
            
            # 如果启用增强特征，检测并添加
            enhanced_features_used = []
            if use_enhanced_features:
                for col in self.enhanced_feature_columns:
                    if col in df.columns:
                        available_features.append(col)
                        enhanced_features_used.append(col)
                
                if enhanced_features_used:
                    print(f"   ✓ 增强特征: {len(enhanced_features_used)} 个")
                    print(f"     {enhanced_features_used}")
                else:
                    print(f"   ⚠️  数据中未找到增强特征，使用基础特征")
            
            # 更新实际使用的特征列表
            self.feature_columns = available_features
            print(f"   📊 总计使用 {len(self.feature_columns)} 个特征")
                
            # 清除因特征工程 (Lag/Rolling) 产生的 NaN 行
            # 这些行通常位于数据集头部
            before_drop = len(df)
            df.dropna(inplace=True)
            after_drop = len(df)
            if before_drop != after_drop:
                print(f"   ✂️  已删除 {before_drop - after_drop} 行包含 NaN 的样本 (Lag/Rolling start-up)")
            
            # 准备特征和目标变量
            print(f"\n📊 准备训练数据...")
            X = df[self.feature_columns].copy()
            y = df[self.target_column].copy()
            
            print(f"   - 特征列: {self.feature_columns}")
            print(f"   - 目标变量: {self.target_column}")
            print(f"   - 数据形状: X={X.shape}, y={y.shape}")
            
            # 划分训练集和测试集
            # 【修复】时间序列数据必须按时间顺序拆分，避免数据泄漏
            print(f"\n✂️  划分数据集 (训练集: {int((1-test_size)*100)}%, 测试集: {int(test_size*100)}%)...")
            
            if use_time_series_cv:
                # 时间序列模式：按时间顺序拆分，测试集为严格未来数据
                # 确保数据按 Date 排序（如果 Date 列存在）
                if 'Date' in df.columns:
                    sort_idx = df['Date'].argsort()
                    X = X.iloc[sort_idx].reset_index(drop=True)
                    y = y.iloc[sort_idx].reset_index(drop=True)
                    print(f"   ✓ 已按时间顺序排序数据")
                
                # 按时间顺序拆分：最后 test_size 比例作为严格未来 holdout
                split_idx = int(len(X) * (1 - test_size))
                X_train = X.iloc[:split_idx].copy()
                X_test = X.iloc[split_idx:].copy()
                y_train = y.iloc[:split_idx].copy()
                y_test = y.iloc[split_idx:].copy()
                print(f"   ✓ 时间序列拆分：测试集为严格未来数据 (避免数据泄漏)")
            else:
                # 非时间序列模式：保持原有随机拆分行为（向后兼容）
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=test_size, random_state=random_state
                )
                print(f"   ⚠️  随机拆分模式 (仅用于非时间序列数据)")
            
            print(f"   - 训练集: {X_train.shape[0]} 样本")
            print(f"   - 测试集: {X_test.shape[0]} 样本")
            
            # 记录配置状态
            self.use_log_transform = use_log_transform
            
            # ================================================================
            # 异常值过滤 (Anomaly Detection) - 仅针对训练集
            # ================================================================
            if remove_outliers:
                print(f"\n🧹 执行异常值过滤 (IQR)...")
                # 计算 IQR
                Q1 = y_train.quantile(0.25)
                Q3 = y_train.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                # 过滤索引
                # 注意：这里我们同时需要过滤 X_train 和 y_train
                mask = (y_train >= lower_bound) & (y_train <= upper_bound)
                outliers_count = len(y_train) - mask.sum()
                
                if outliers_count > 0:
                     X_train = X_train[mask]
                     y_train = y_train[mask]
                     print(f"   ✓ 已移除 {outliers_count} 个异常样本")
                     print(f"     阈值区间: [{lower_bound:.2f}, {upper_bound:.2f}]")
                else:
                     print(f"   ✓ 未发现显著异常值")
            
            # ================================================================
            # 目标变量对数变换 (Log Transform)
            # ================================================================
            if use_log_transform:
                print(f"\n📉执行 Log1p 变换...")
                # 检查负值
                if (y_train < 0).any():
                     print(f"   ⚠️  y_train 包含负值，无法进行 Log 变换，自动禁用")
                     self.use_log_transform = False
                else:
                     y_train = np.log1p(y_train)
                     # y_test 不变换，保持原始比例用于评估
                     print(f"   ✓ y_train 已进行 np.log1p 变换")

            # ================================================================
            # 自动模型选择与训练
            # ================================================================
            if auto_select_model and model_type == 'auto':
                print(f"\n🤖 自动模型选择模式...")
                best_model, best_params, selection_info = self._auto_select_best_model(
                    X_train, y_train, X_test, y_test, random_state,
                    use_time_series_cv=use_time_series_cv,
                    n_splits=cv_folds,
                    perform_tuning=tune_hyperparameters
                )
                self.model = best_model
                selected_model_type = selection_info['winner']
                hyperparameters = best_params
            else:
                # 手动模式：使用指定的模型类型
                print(f"\n🌲 训练 {model_type} 模型...")
                self.model, hyperparameters = self._create_model(
                    model_type, n_estimators, random_state
                )
                self.model.fit(X_train, y_train)
                selected_model_type = model_type
                selection_info = {'winner': model_type, 'candidates_evaluated': [model_type]}
            
            print(f"   ✓ 模型训练完成! (类型: {selected_model_type})")
            
            # 评估模型
            print(f"\n📈 评估模型性能...")
            
            # 训练集预测
            y_train_pred = self.model.predict(X_train)
            
            # 还原
            if self.use_log_transform:
                y_train = np.expm1(y_train)
                y_train_pred = np.expm1(y_train_pred)
                
            train_mae = mean_absolute_error(y_train, y_train_pred)
            train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
            
            # 测试集预测
            y_test_pred = self.model.predict(X_test)
            
            if self.use_log_transform:
                y_test_pred = np.expm1(y_test_pred)
                
            test_mae = mean_absolute_error(y_test, y_test_pred)
            test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
            
            # 计算 R² Score (测试集)
            test_r2 = r2_score(y_test, y_test_pred)
            
            # 计算 MAPE (测试集) - Mean Absolute Percentage Error
            # 避免分母为 0
            mask = y_test.values != 0
            if np.sum(mask) > 0:
                test_mape = np.mean(np.abs((y_test.values[mask] - y_test_pred[mask]) / y_test.values[mask])) * 100
            else:
                test_mape = 0.0
            
            print(f"\n   训练集性能:")
            print(f"      - MAE:  {train_mae:.2f} kW")
            print(f"      - RMSE: {train_rmse:.2f} kW")
            
            print(f"\n   测试集性能:")
            print(f"      - MAE:  {test_mae:.2f} kW")
            print(f"      - RMSE: {test_rmse:.2f} kW")
            print(f"      - R²:   {test_r2:.4f}")
            print(f"      - MAPE: {test_mape:.2f}%")

            # ------------------------------------------------------------
            # 验证信息汇总 (用于元数据和前端展示)
            # ------------------------------------------------------------
            validation_summary = {
                'method': 'TimeSeriesSplit' if use_time_series_cv else 'HoldOut',
                'cv_folds': cv_folds if use_time_series_cv else None,
                'holdout_mae': float(test_mae),
                'holdout_rmse': float(test_rmse),
                'holdout_r2': float(test_r2),
                'holdout_mape': float(test_mape / 100),  # 统一为小数
            }

            # 如果有交叉验证详情，记录当前胜出模型的均值和波动
            if auto_select_model and model_type == 'auto' and selection_info:
                winner_name = selection_info.get('winner')
                cv_detail = (selection_info.get('cv_details') or {}).get(winner_name, {})
                if cv_detail:
                    validation_summary.update({
                        'cv_mae_mean': cv_detail.get('cv_mae_mean'),
                        'cv_mae_std': cv_detail.get('cv_mae_std'),
                        'cv_scores': cv_detail.get('cv_scores')
                    })

            # ================================================================
            # 生成评估报告 (使用 EvaluationService - Phase 1 新增)
            # ================================================================
            try:
                from services.evaluation_service import EvaluationService
                
                print(f"\n📄 生成评估报告...")
                
                # 计算详细指标
                eval_metrics = EvaluationService.calculate_time_series_metrics(
                    y_true=y_test.values,
                    y_pred=y_test_pred,
                    cv_scores=validation_summary.get('cv_scores')
                )
                
                # 构建模型信息
                model_info = {
                    'name': selected_model_type,
                    'type': self._get_model_type_name(),
                    'n_features': len(self.feature_columns),
                    'n_train_samples': len(X_train),
                    'hyperparameters': hyperparameters
                }
                
                # 生成 Markdown 报告
                report_content = EvaluationService.generate_report(
                    metrics=eval_metrics,
                    model_info=model_info,
                    comparison_df=None,  # 可扩展为多模型对比
                    output_path=None  # 不保存本地文件
                )
                
                # 上传报告到 Firebase Storage
                report_path = 'models/evaluation_report.md'
                self.storage_service.bucket.blob(report_path).upload_from_string(
                    report_content,
                    content_type='text/markdown; charset=utf-8'
                )
                print(f"   ✓ 评估报告已保存到: {report_path}")
                
                # 将指标存入 validation_summary 供元数据使用
                validation_summary['evaluation_metrics'] = eval_metrics
                
            except Exception as eval_err:
                print(f"   ⚠️ 生成评估报告失败: {str(eval_err)}")

            # 数据覆盖范围
            data_coverage = None
            if 'Date' in df.columns:
                date_min = df['Date'].min()
                date_max = df['Date'].max()
                span_days = None
                try:
                    span_days = int((date_max - date_min).days)
                except Exception:
                    span_days = None

                data_coverage = {
                    'start': date_min.isoformat() if hasattr(date_min, 'isoformat') else str(date_min),
                    'end': date_max.isoformat() if hasattr(date_max, 'isoformat') else str(date_max),
                    'span_days': span_days,
                    'rows': int(len(df))
                }
            
            # 特征重要性
            print(f"\n🔍 特征重要性:")
            importances = None
            
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
            elif isinstance(self.model, VotingRegressor):
                # 尝试计算平均特征重要性
                try:
                    all_importances = [est.feature_importances_ for est in self.model.estimators_]
                    importances = np.mean(all_importances, axis=0)
                except Exception:
                     pass
            
            if importances is not None:
                feature_importance = pd.DataFrame({
                    'Feature': self.feature_columns,
                    'Importance': importances
                }).sort_values('Importance', ascending=False)
                
                for _, row in feature_importance.iterrows():
                    print(f"      - {row['Feature']}: {row['Importance']:.4f}")
            else:
                print("      (当前模型不支持特征重要性输出)")
                feature_importance = pd.DataFrame(columns=['Feature', 'Importance'])
            
            # 保存模型到 Firebase Storage
            print(f"\n💾 保存模型到 Firebase Storage: {self.firebase_model_path}")
            temp_model_path = None
            try:
                # Step A: 创建临时文件
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.joblib', delete=False) as tmp_file:
                    temp_model_path = tmp_file.name
                    print(f"   - 临时文件: {temp_model_path}")
                
                # Step B: 保存模型到临时文件
                joblib.dump(self.model, temp_model_path)
                print(f"   ✓ 模型已保存到临时文件")
                
                # Step B-2: 保存模型到本地持久化路径 (用于开发环境调试)
                # 仅在非 GAE 环境下执行，避免 Read-only file system 错误
                if not self._is_gae_environment():
                    try:
                        # 确保存储目录存在
                        self.local_model_path.parent.mkdir(parents=True, exist_ok=True)
                        joblib.dump(self.model, self.local_model_path)
                        print(f"   ✓ 模型已备份到本地路径: {self.local_model_path}")
                    except Exception as local_e:
                        print(f"   ⚠️  无法保存本地模型副本: {str(local_e)}")
                else:
                    print(f"   ℹ️  GAE 环境：跳过本地模型备份")

                
                # Step C: 上传到 Firebase Storage
                with open(temp_model_path, 'rb') as f:
                    self.storage_service.upload_file(
                        file_data=f,
                        destination_path=self.firebase_model_path,
                        content_type='application/octet-stream'
                    )
                print(f"   ✓ 模型已上传到 Firebase Storage")
                
            except Exception as e:
                print(f"   ❌ 模型保存失败: {str(e)}")
                raise
            finally:
                # Step D: 清理临时文件
                if temp_model_path and os.path.exists(temp_model_path):
                    try:
                        os.remove(temp_model_path)
                        print(f"   🧹 已清理临时模型文件")
                    except Exception as e:
                        print(f"   ⚠️  清理临时模型文件失败: {str(e)}")
            
            print("\n" + "="*80)
            print("✅ 模型训练完成!")
            print("="*80 + "\n")
            
            # 保存模型元数据到 Firebase Storage (全局元数据)
            # 获取模型类型名称
            model_type_name = self._get_model_type_name()
            
            try:
                metadata = {
                    'model_type': model_type_name,
                    'model_version': datetime.now().strftime('%Y%m%d_%H%M%S'),
                    'trained_at': datetime.now().isoformat(),
                    'metrics': {
                        'train_mae': float(train_mae),
                        'train_rmse': float(train_rmse),
                        'test_mae': float(test_mae),
                        'test_rmse': float(test_rmse),
                        'r2_score': float(test_r2),
                        'mape': float(test_mape / 100),  # 存储为小数形式, 5% -> 0.05
                    },
                    'training_samples': len(df),
                    'data_source': 'CAISO Real-Time Stream',
                    'feature_importance': feature_importance.to_dict('records'),
                    'model_path': self.firebase_model_path,
                    'status': 'active',
                    # 数据覆盖信息
                    'data_coverage': data_coverage,
                    # 【新增】单位标注信息（向后兼容，不改变数值）
                    'units': {
                        'target_variable': self.target_column,
                        'target_unit': 'kW',  # Site_Load 的单位
                        'load_unit_multiplier': 1.0,  # 1.0 表示原始值，1000 表示 MW->kW
                        'price_unit': 'CNY/kWh',  # 电价单位
                        'temperature_unit': '°C',  # 温度单位
                        'note': 'CAISO 原始数据为 MW，已转换为 kW 存储'
                    },
                    # 特征工程信息
                    'feature_engineering': {
                        'total_features': len(self.feature_columns),
                        'base_features': len(self.base_feature_columns),
                        'enhanced_features': len(enhanced_features_used) if use_enhanced_features else 0,
                        'enhanced_features_list': enhanced_features_used if use_enhanced_features else [],
                        'use_enhanced': use_enhanced_features
                    },
                    # 验证摘要 (交叉验证 / 留出验证)
                    'validation_summary': validation_summary,
                    # 【新增】训练配置记录（便于复现）
                    'training_config': {
                        'test_size': test_size,
                        'random_state': random_state,
                        'use_time_series_cv': use_time_series_cv,
                        'cv_folds': cv_folds if use_time_series_cv else None,
                        'cv_folds': cv_folds if use_time_series_cv else None,
                        'time_series_split': use_time_series_cv,  # 标记是否使用了时间序列拆分
                        'use_log_transform': use_log_transform,   # 记录是否使用了 Log 变换
                        'remove_outliers': remove_outliers,       # 记录是否使用了异常值过滤
                        'hyperparameter_tuning': tune_hyperparameters # 记录是否启用了超参数搜索
                    }
                }
                
                # 添加自动模型选择信息
                if auto_select_model and model_type == 'auto':
                    metadata['auto_selection'] = {
                        'enabled': True,
                        'candidates_evaluated': selection_info.get('candidates_evaluated', []),
                        'winner': selection_info.get('winner', 'unknown'),
                        'improvement_over_baseline': selection_info.get('improvement', 'N/A'),
                        'all_scores': selection_info.get('all_scores', {}),
                        # 新增：交叉验证信息
                        'validation_method': selection_info.get('validation_method', 'HoldOut'),
                        'cv_folds': selection_info.get('cv_folds'),
                        'cv_details': selection_info.get('cv_details')
                    }
                    metadata['hyperparameters'] = hyperparameters
                
                self._save_model_metadata(metadata)
            except Exception as e:
                print(f"   ⚠️  保存模型元数据失败: {str(e)}")
            
            # 返回评估指标
            return {
                'train_mae': train_mae,
                'train_rmse': train_rmse,
                'test_mae': test_mae,
                'test_rmse': test_rmse,
                'r2_score': test_r2,  # 新增
                'mape': test_mape / 100,  # 新增 (小数形式)
                'feature_importance': feature_importance.to_dict('records'),
                'model_type': model_type_name,
                'hyperparameters': hyperparameters if auto_select_model else {'n_estimators': n_estimators},
                'auto_selection': selection_info if auto_select_model and model_type == 'auto' else None,
                # 新增：特征工程和交叉验证信息
                'feature_engineering': {
                    'total_features': len(self.feature_columns),
                    'enhanced_features_used': enhanced_features_used if use_enhanced_features else []
                },
                'validation': {
                    'method': 'TimeSeriesSplit' if use_time_series_cv else 'HoldOut',
                    'cv_folds': cv_folds if use_time_series_cv else None,
                    'summary': validation_summary
                },
                'data_coverage': data_coverage
            }
        
        finally:
            # 清理临时文件
            if temp_data_path and os.path.exists(temp_data_path):
                try:
                    os.remove(temp_data_path)
                    print(f"🧹 清理临时训练数据文件")
                except Exception as e:
                    print(f"⚠️  清理临时文件失败: {str(e)}")
    
    def load_model(self) -> bool:
        """
        加载已保存的模型（优先从 Firebase Storage）
        同时加载模型元数据以恢复正确的特征列表
        
        Returns:
            是否加载成功
            
        Raises:
            FileNotFoundError: 模型文件不存在
            Exception: 加载模型时出错
        """
        print(f"📂 加载模型...")
        temp_model_path = None
        
        try:
            # Step A: 检查 Firebase Storage 中是否存在模型
            print(f"   - 检查 Firebase Storage: {self.firebase_model_path}")
            
            if self.storage_service.file_exists(self.firebase_model_path):
                print(f"   ✓ Firebase Storage 中存在模型")
                
                # Step B: 下载到临时目录
                temp_model_path = self.storage_service.download_to_temp(self.firebase_model_path)
                
                if temp_model_path is None:
                    raise Exception("从 Firebase Storage 下载模型失败")
                
                print(f"   ✓ 模型已下载到: {temp_model_path}")
                
                # Step C: 从临时文件加载模型
                self.model = joblib.load(temp_model_path)
                print(f"   ✓ 模型加载成功 (来源: Firebase Storage)")
                
                # Step D: 加载模型元数据以恢复特征列表
                self._load_feature_columns_from_metadata()
                
                return True
            
            else:
                # Step E: Firebase 中没有模型，尝试加载本地兜底模型
                print(f"   ⚠️  Firebase Storage 中无模型，尝试加载本地兜底模型")
                
                if not self.local_model_path.exists():
                    raise FileNotFoundError(
                        f"模型文件不存在:\n"
                        f"  - Firebase Storage: {self.firebase_model_path} (不存在)\n"
                        f"  - 本地路径: {self.local_model_path} (不存在)\n"
                        f"请先调用 train_model() 训练模型。"
                    )
                
                self.model = joblib.load(self.local_model_path)
                print(f"   ✓ 模型加载成功 (来源: 本地兜底文件)")
                
                # 同样尝试加载元数据
                self._load_feature_columns_from_metadata()
                
                return True
        
        except Exception as e:
            raise Exception(f"加载模型时出错: {str(e)}")
        
        finally:
            # 清理临时文件
            if temp_model_path and os.path.exists(temp_model_path):
                try:
                    os.remove(temp_model_path)
                    print(f"   🧹 已清理临时模型文件")
                except Exception as e:
                    print(f"   ⚠️  清理临时模型文件失败: {str(e)}")
    
    def _load_history_context(self, end_time: datetime, window_size: int = 200) -> pd.DataFrame:
        """
        加载用于特征构建的历史数据上下文
        
        Args:
            end_time: 截止时间（不包含）
            window_size: 需要加载的历史窗口大小（小时）
            
        Returns:
            包含 Site_Load, Temperature 等列的历史 DataFrame
        """
        print(f"📖 加载历史上下文 (截止 {end_time})...")
        
        # 尝试加载全量数据文件
        # 在生产环境中，这应该优化为只从数据库/Storage读取部分数据
        # 但为了保持一致性，我们这里复用训练数据文件
        data_path = None
        
        # 尝试从本地或临时目录查找
        possible_paths = [
            self.back_dir.parent / 'data' / 'processed' / 'cleaned_energy_data_all.csv', # 开发环境
            Path('/tmp/cleaned_energy_data_all.csv'), # 临时目录
            self.back_dir / 'data' / 'processed' / 'cleaned_energy_data_all.csv',
        ]
        
        for path in possible_paths:
            if path.exists():
                data_path = path
                break
                
        if data_path is None:
            # 尝试从 Storage 下载
            print("   📥 本地未找到数据，尝试从 Firebase Storage 下载...")
            try:
                data_path = self.storage_service.download_to_temp('data/processed/cleaned_energy_data_all.csv')
            except Exception as e:
                print(f"   ⚠️  无法下载历史数据: {e}")
                
        if data_path:
            df = pd.read_csv(data_path, parse_dates=['Date'])
            # 筛选截止时间之前的数据
            history = df[df['Date'] < end_time].tail(window_size).copy()
            if len(history) < 168:
                print(f"   ⚠️  历史数据不足 168 小时 (实际: {len(history)}), 特征可能不准确")
            return history
        else:
            print("   ⚠️  无法加载历史上下文，将使用全 0 填充 (仅用于测试/冷启动)")
            # 创建虚拟历史数据
            dates = [end_time - timedelta(hours=i) for i in range(window_size, 0, -1)]
            return pd.DataFrame({
                'Date': dates,
                'Site_Load': [0.0] * window_size,
                'Temperature': [25.0] * window_size,
                'Hour': [d.hour for d in dates],
                'DayOfWeek': [d.weekday() for d in dates]
            })

    def predict_next_24h(
        self,
        start_time: Union[str, datetime],
        temp_forecast_list: Optional[List[float]] = None,
        temp_adjust_delta: float = 0.0
    ) -> List[Dict[str, Union[datetime, float]]]:
        """
        预测未来24小时的能源负载 (递归预测模式)
        
        Args:
            start_time: 开始时间
            temp_forecast_list: 温度预测列表
            temp_adjust_delta: 温度调整值 (用于 What-If 分析)
            
        Returns:
            预测结果列表
        """
        if self.model is None:
            raise ValueError("模型未加载，请先调用 load_model() 或 train_model()")
        
        if isinstance(start_time, str):
            start_time = pd.to_datetime(start_time)
        
        # 验证温度预测列表长度
        if temp_forecast_list is not None and len(temp_forecast_list) != 24:
            raise ValueError(f"temp_forecast_list 长度必须为 24，当前为 {len(temp_forecast_list)}")
            
        print(f"\n🔮 递归预测未来24小时负载 (从 {start_time} 开始)...")
        
        # 1. 加载历史上下文 (用于构建 Lag/Rolling 特征)
        # 我们至少需要过去 168 小时的数据
        history_df = self._load_history_context(start_time, window_size=200)
        
        # 转换为 list 以便高效 append
        history_loads = history_df['Site_Load'].tolist()
        history_temps = history_df['Temperature'].tolist() # 历史温度
        
        # 如果未提供温度预测，使用持久性预测 (昨天的温度)
        if temp_forecast_list is None:
            if len(history_temps) >= 24:
                # 使用过去 24 小时的数据作为基准 (Persistence Forecast)
                print("   ℹ️  未提供温度预测，使用过去24小时温度作为基准 (Persistence Forecast)")
                temp_forecast_list = history_temps[-24:]
            else:
                # 历史数据不足，回退到默认值
                print("   ⚠️  历史温度不足，使用默认 25.0°C")
                temp_forecast_list = [25.0] * 24
        
        # 应用温度调整 (What-If Analysis)
        if temp_adjust_delta != 0.0:
            print(f"   🌡️  应用温度调整: {temp_adjust_delta:+.1f}°C")
            temp_forecast_list = [t + temp_adjust_delta for t in temp_forecast_list]
        
        predictions = []
        prediction_results = []
        
        # 2. 递归预测循环
        current_time = start_time
        
        for i in range(24):
            # A. 特征构建
            hour = current_time.hour
            day_of_week = current_time.weekday()
            temperature = temp_forecast_list[i]
            price = self._get_price(hour)
            
            # 构建高级特征
            # 注意：history_loads 的最后一个元素是 t-1 时刻的负载
            
            # Lag Features
            lag_1h = history_loads[-1] if len(history_loads) >= 1 else 0
            lag_24h = history_loads[-24] if len(history_loads) >= 24 else 0
            lag_168h = history_loads[-168] if len(history_loads) >= 168 else 0
            
            # Rolling Features
            # 取最近 N 个点计算均值/标准差
            # 【修复】使用 ddof=1 与训练时 pandas.rolling().std() 保持一致
            roll_6h_mean = np.mean(history_loads[-6:]) if len(history_loads) >= 6 else lag_1h
            roll_6h_std = np.std(history_loads[-6:], ddof=1) if len(history_loads) >= 6 else 0
            roll_24h_mean = np.mean(history_loads[-24:]) if len(history_loads) >= 24 else lag_1h
            
            # Interaction Features (基础)
            temp_x_hour = temperature * hour
            lag24_x_dow = lag_24h * day_of_week
            
            # 组装基础特征向量
            feature_dict = {
                'Hour': hour,
                'DayOfWeek': day_of_week,
                'Temperature': temperature,
                'Price': price,
                'Lag_1h': lag_1h,
                'Lag_24h': lag_24h,
                'Lag_168h': lag_168h,
                'Rolling_Mean_6h': roll_6h_mean,
                'Rolling_Std_6h': roll_6h_std,
                'Rolling_Mean_24h': roll_24h_mean,
                'Temp_x_Hour': temp_x_hour,
                'Lag24_x_DayOfWeek': lag24_x_dow
            }
            
            # 添加增强特征（如果模型需要）
            # 检查模型是否使用增强特征
            if len(self.feature_columns) > 12:
                # 时间特征
                month = current_time.month
                day_of_month = current_time.day
                week_of_year = current_time.isocalendar()[1]
                
                # 季节 (北半球)
                if month in [3, 4, 5]:
                    season = 0  # 春
                elif month in [6, 7, 8]:
                    season = 1  # 夏
                elif month in [9, 10, 11]:
                    season = 2  # 秋
                else:
                    season = 3  # 冬
                
                # 是否周末
                is_weekend = 1 if day_of_week >= 5 else 0
                
                # 是否节假日（美国加州）
                # 优化: 避免在循环中重复初始化
                if not hasattr(self, '_holidays_cache'):
                    try:
                        import holidays
                        # 使用 subdiv 替代 deprecated 的 state 参数
                        self._holidays_cache = holidays.US(subdiv='CA')
                    except ImportError:
                        self._holidays_cache = None
                    except Exception:
                        # 兼容旧版本 holidays (如不支持 subdiv)
                        try:
                            import holidays
                            self._holidays_cache = holidays.US(state='CA')
                        except:
                            self._holidays_cache = None

                if self._holidays_cache:
                    is_holiday = 1 if current_time.date() in self._holidays_cache else 0
                else:
                    is_holiday = is_weekend  # 简化：周末视为假日
                
                # 增强交互特征
                temp_x_season = temperature * season
                lag24_x_is_weekend = lag_24h * is_weekend
                hour_x_is_holiday = hour * is_holiday
                
                # 周期编码
                month_sin = np.sin(2 * np.pi * month / 12)
                month_cos = np.cos(2 * np.pi * month / 12)
                hour_sin = np.sin(2 * np.pi * hour / 24)
                hour_cos = np.cos(2 * np.pi * hour / 24)
                
                # 添加增强特征
                feature_dict.update({
                    'Month': month,
                    'Season': season,
                    'IsWeekend': is_weekend,
                    'IsHoliday': is_holiday,
                    'DayOfMonth': day_of_month,
                    'WeekOfYear': week_of_year,
                    'Temp_x_Season': temp_x_season,
                    'Lag24_x_IsWeekend': lag24_x_is_weekend,
                    'Hour_x_IsHoliday': hour_x_is_holiday,
                    'Month_Sin': month_sin,
                    'Month_Cos': month_cos,
                    'Hour_Sin': hour_sin,
                    'Hour_Cos': hour_cos
                })
                
                # ================================================================
                # 分位数与波动率特征 (Phase 1 新增，修复 Quantile_95_24h KeyError)
                # ================================================================
                # 计算过去 24 小时的分位数和波动率
                if len(history_loads) >= 24:
                    recent_24h = history_loads[-24:]
                    quantile_95_24h = np.percentile(recent_24h, 95)
                    quantile_05_24h = np.percentile(recent_24h, 5)
                    roll_24h_std = np.std(recent_24h, ddof=1)
                    # 波动率 = 标准差 / 均值 (变异系数)
                    volatility_24h = roll_24h_std / roll_24h_mean if roll_24h_mean > 0 else 0
                else:
                    # 历史数据不足时使用合理默认值
                    quantile_95_24h = lag_1h * 1.2 if lag_1h > 0 else 0
                    quantile_05_24h = lag_1h * 0.8 if lag_1h > 0 else 0
                    volatility_24h = 0.1  # 默认 10% 波动
                
                # 价格变化特征
                # 在预测循环中，我们需要与上一时刻的价格对比
                if i == 0:
                    # 第一个时间步，使用历史最后一个价格（如果有）
                    # 简化处理：假设上一小时价格与当前价格比较
                    prev_hour = (hour - 1) % 24
                    prev_price = self._get_price(prev_hour)
                else:
                    prev_price = prediction_results[-1]['price']
                price_change = abs(price - prev_price)
                
                # 负载变化特征
                load_change_1h = lag_1h - (history_loads[-2] if len(history_loads) >= 2 else lag_1h)
                load_change_pct_1h = (load_change_1h / history_loads[-2] * 100) if len(history_loads) >= 2 and history_loads[-2] != 0 else 0
                
                # 添加分位数和波动率特征
                feature_dict.update({
                    'Quantile_95_24h': quantile_95_24h,
                    'Quantile_05_24h': quantile_05_24h,
                    'Volatility_24h': volatility_24h,
                    'Price_Change': price_change,
                    'Load_Change_1h': load_change_1h,
                    'Load_Change_Pct_1h': load_change_pct_1h
                })
            
            # 确保特征顺序与模型一致
            features = pd.DataFrame([{col: feature_dict[col] for col in self.feature_columns}])
            
            # B. 单步推理
            pred_log = float(self.model.predict(features)[0])
            
            # 如果模型使用了 Log 变换，需要还原
            if hasattr(self, 'use_log_transform') and self.use_log_transform:
                pred_load = float(np.expm1(pred_log))
            else:
                pred_load = pred_log
            
            # 【安全检查】强制约束预测值为非负 (物理常识)
            pred_load = max(0.0, pred_load)
            
            # C. 更新历史序列 (递归关键)
            # 将预测值作为"真实值"加入历史，用于下一步预测
            history_loads.append(pred_load)
            predictions.append(pred_load)
            
            # D. 记录结果
            prediction_results.append({
                'datetime': current_time,
                'predicted_load': pred_load,
                'temperature': temperature,
                'price': price,
                'hour': hour,
                'day_of_week': day_of_week
            })
            
            # 时间步进
            current_time += timedelta(hours=1)
            
        print(f"   ✓ 递归预测完成")
        return prediction_results

    def predict_single(self, *args, **kwargs):
        """
        单点预测已被递归预测取代，且不仅依赖简单输入。
        为保持接口兼容抛出异常或仅做简单处理。
        """
        raise NotImplementedError("单点预测 (predict_single) 已废弃，请使用 predict_next_24h 进行序列预测。")
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        获取模型的全局特征重要性
        
        使用随机森林内置的 feature_importances_ 属性，
        反映各特征在整体预测中的平均贡献
        
        Returns:
            特征名到重要性分数的映射字典
            
        Raises:
            ValueError: 模型未加载
        """
        if self.model is None:
            raise ValueError("模型未加载，请先调用 load_model() 或 train_model()")
        
        importances = None
        if hasattr(self.model, 'feature_importances_'):
             importances = self.model.feature_importances_
        elif isinstance(self.model, VotingRegressor):
             try:
                 all_importances = [est.feature_importances_ for est in self.model.estimators_]
                 importances = np.mean(all_importances, axis=0)
             except:
                 pass
                 
        if importances is None:
             # 如果无法获取，返回空字典或默认均匀分布
             return {col: 0.0 for col in self.feature_columns}
             
        # 【修复】归一化特征重要性，确保总和为 1.0
        # XGBoost/LightGBM 在 VotingRegressor 中可能返回未归一化的值 (如 gain/cover)
        total_importance = np.sum(importances)
        if total_importance > 0:
            importances = importances / total_importance
             
        importance_dict = dict(zip(
            self.feature_columns,
            [float(v) for v in importances]
        ))
        
        # 按重要性降序排序
        sorted_importance = dict(sorted(
            importance_dict.items(),
            key=lambda x: x[1],
            reverse=True
        ))
        
        return sorted_importance
    
    def explain_prediction(
        self,
        hour: int,
        day_of_week: int,
        temperature: float,
        price: float = None
    ) -> Dict[str, Any]:
        """
        使用 SHAP 解释单次预测
        
        为给定输入提供详细的特征贡献分析，
        展示每个特征如何影响最终预测值
        
        Args:
            hour: 小时 (0-23)
            day_of_week: 星期几 (0-6)
            temperature: 温度 (°C)
            price: 电价，如果为None则自动根据hour计算
            
        Returns:
            包含以下字段的字典:
            - base_value: 模型基准预测值（训练数据的平均值）
            - predicted_value: 实际预测值
            - feature_contributions: 各特征的贡献值字典
            - interpretation: 人类可读的解释文字
        """
        try:
            import shap
            
            # 检查模型是否已加载
            if self.model is None:
                raise ValueError("模型未加载，请先调用 load_model() 或 train_model()")

            # 构建特征 DataFrame
            # 【修复】如果 price 为 None，使用统一的 _get_price 方法计算（与推理一致）
            if price is None:
                price = self._get_price(hour)
            
            # 尝试从历史数据获取滞后特征，如果没有则使用合理的默认值
            # 默认值基于典型的负载模式
            default_load = 150.0  # 典型平均负载 (kW)
            
            # 构建与训练时相同的特征 DataFrame（包含所有12个特征）
            features = pd.DataFrame({
                'Hour': [hour],
                'DayOfWeek': [day_of_week],
                'Temperature': [temperature],
                'Price': [price],
                'Lag_1h': [default_load],  # 1小时前的负载
                'Lag_24h': [default_load],  # 24小时前的负载
                'Lag_168h': [default_load],  # 168小时(一周)前的负载
                'Rolling_Mean_6h': [default_load],  # 6小时滚动平均
                'Rolling_Std_6h': [default_load * 0.1],  # 6小时滚动标准差
                'Rolling_Mean_24h': [default_load],  # 24小时滚动平均
                'Temp_x_Hour': [temperature * hour],  # 温度与小时的交互特征
                'Lag24_x_DayOfWeek': [default_load * day_of_week]  # 24小时滞后与星期的交互
            })
            
            # 确保特征列顺序与训练时一致
            features = features[self.feature_columns]
            
            # 使用 TreeExplainer 解释随机森林模型
            # 只有当 explainer 尚未初始化时才创建，避免重复计算
            if not hasattr(self, '_shap_explainer') or self._shap_explainer is None:
                self._shap_explainer = shap.TreeExplainer(self.model)
                
            # 计算 SHAP 值
            shap_values = self._shap_explainer.shap_values(features)
            
            # 获取期望值 (base value)
            # 对于回归模型，expected_value 应该是一个标量
            base_value = self._shap_explainer.expected_value
            if isinstance(base_value, np.ndarray):
                base_value = base_value[0]
                
            # 获取当前预测的 SHAP 值
            # shap_values 对于回归可能是 (n_samples, n_features)
            # 我们只需要第一个样本
            current_shap_values = shap_values[0]
            
            # 预测值 = base_value + sum(shap_values)
            predicted_value = base_value + np.sum(current_shap_values)
            
            # 构建特征贡献列表
            contributions = []
            for i, col in enumerate(self.feature_columns):
                contributions.append({
                    'feature': col,
                    'value': float(features.iloc[0][col]),
                    'contribution': float(current_shap_values[i])
                })
            
            # 按贡献绝对值排序
            contributions.sort(key=lambda x: abs(x['contribution']), reverse=True)
            
            # 生成人类可读的解释文字
            top_feature = contributions[0]
            direction = "增加" if top_feature['contribution'] > 0 else "减少"
            interpretation = (
                f"{top_feature['feature']} 是影响最大的因素，"
                f"它使得预测负载{direction}了 {abs(top_feature['contribution']):.1f} kW。"
            )

            return {
                'base_value': float(base_value),
                'predicted_value': float(predicted_value),
                'feature_contributions': contributions,
                'interpretation': interpretation
            }
            
        except Exception as e:
            print(f"解释预测失败: {str(e)}")
            return None

    def evaluate_recent_performance(self, hours: int = 24) -> Dict[str, Union[float, str]]:
        """
        评估模型在最近一段时间的表现 (在线监控)
        通过回测最近的真实数据来计算指标
        
        Args:
            hours: 回测的小时数 (默认 24)
            
        Returns:
            包含评估指标的字典 (mape, r2, last_update_time)
        """
        print(f"\n🔍 开始在线模型评估 (最近 {hours} 小时)...")
        
        try:
            # 1. 动态下载最新数据 (从 Firestore/Storage 持久化的 CSV)
            from services.storage_service import StorageService
            storage_service = StorageService()
            
            # 尝试下载最新的 cleaned_energy_data_all.csv
            data_path = storage_service.download_to_temp('data/processed/cleaned_energy_data_all.csv')
            
            if not data_path:
                print("   ⚠️ 无法下载数据文件，跳过评估")
                return {'status': 'no_data'}
                
            # 2. 读取数据
            df = pd.read_csv(data_path, parse_dates=['Date'])
            
            # 3. 基于时间截取最近 N 小时的数据 (避免数据中断导致 tail(N) 跨度过大)
            last_time = df['Date'].max()
            start_time = last_time - timedelta(hours=hours)
            
            # 筛选时间窗口内的数据
            recent_df = df[df['Date'] > start_time].copy()
            
            # 检查样本量
            # 理论上应该有 hours 个样本，允许有一点缺失 (e.g. > 50%)
            min_samples = int(hours * 0.5) 
            if len(recent_df) < min_samples:
                print(f"   ⚠️ 最近 {hours} 小时内数据样本不足 ({len(recent_df)} < {min_samples})，跳过评估")
                return {
                    'status': 'insufficient_data',
                    'message': f'Insufficient data in last {hours}h: found {len(recent_df)} samples'
                }
                
            # 4. 准备特征和真实值
            # 【修复】检查并自动补算缺失特征
            missing_features = [col for col in self.feature_columns if col not in recent_df.columns]
            if missing_features:
                print(f"   ⚠️ 检测到缺失特征: {missing_features}")
                print(f"   🔧 尝试自动补算...")
                
                try:
                    from services.data_processor import EnergyDataProcessor
                    processor = EnergyDataProcessor()
                    
                    # 确保 Date 是 datetime 类型
                    if recent_df['Date'].dtype == 'object':
                        recent_df['Date'] = pd.to_datetime(recent_df['Date'])
                    
                    # 补算基础时间特征
                    if 'Hour' not in recent_df.columns:
                        recent_df['Hour'] = recent_df['Date'].dt.hour
                    if 'DayOfWeek' not in recent_df.columns:
                        recent_df['DayOfWeek'] = recent_df['Date'].dt.dayofweek
                    if 'Price' not in recent_df.columns:
                        recent_df = processor.add_price_feature(recent_df)
                    
                    # 补算增强时间特征
                    enhanced_time_cols = ['Month', 'Season', 'IsWeekend', 'IsHoliday']
                    if any(c in missing_features for c in enhanced_time_cols):
                        recent_df = processor.add_enhanced_time_features(recent_df)
                    
                    # 补算 Lag/Rolling 特征
                    lag_cols = ['Lag_1h', 'Lag_24h', 'Lag_168h', 'Rolling_Mean_6h', 'Rolling_Std_6h']
                    if any(c in missing_features for c in lag_cols):
                        recent_df = processor.add_advanced_features(recent_df, dropna=False, use_enhanced=True)
                    
                    # 再次检查是否还有缺失
                    still_missing = [col for col in self.feature_columns if col not in recent_df.columns]
                    if still_missing:
                        print(f"   ❌ 仍有无法补算的特征: {still_missing}")
                        return {
                            'status': 'feature_mismatch',
                            'message': f'Cannot compute features: {still_missing}'
                        }
                    print(f"   ✓ 特征补算完成")
                except Exception as fe:
                    print(f"   ❌ 特征补算失败: {str(fe)}")
                    return {
                        'status': 'feature_error',
                        'message': f'Feature computation failed: {str(fe)}'
                    }
            
            # 删除因 Lag/Rolling 产生的 NaN 行
            recent_df = recent_df.dropna(subset=self.feature_columns)
            if len(recent_df) < min_samples:
                print(f"   ⚠️ 删除 NaN 后样本不足 ({len(recent_df)} < {min_samples})")
                return {
                    'status': 'insufficient_data',
                    'message': f'Insufficient valid samples after feature computation'
                }
            
            X_recent = recent_df[self.feature_columns]
            y_true = recent_df[self.target_column].values
            
            # 5. 进行预测
            y_pred = self.model.predict(X_recent)
            
            # 如果模型使用了 Log 变换，需要还原
            if hasattr(self, 'use_log_transform') and self.use_log_transform:
                 y_pred = np.expm1(y_pred)
            
            # 6. 计算指标
            # MAPE: Mean Absolute Percentage Error
            # 避免分母为 0
            mask = y_true != 0
            if np.sum(mask) == 0:
                print("   ⚠️ 所有真实负载均为 0，无法计算 MAPE")
                mape = 0.0
            else:
                mape = (np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)
            
            # R2 Score
            if len(y_true) < 2:
                r2 = 0.0  # 样本太少
            else:
                r2 = r2_score(y_true, y_pred)
            
            # 7. 格式化结果
            # 注意：mape 存储为小数形式 (0.05 = 5%)，以便与前端 percent indicator 直接兼容
            metrics = {
                'status': 'success',
                'mape': round(mape / 100, 4),  # 转换为小数形式 (5.25% -> 0.0525)
                'r2_score': round(r2, 3),  # 使用正确的 key 名称匹配前端
                'sample_count': len(y_true),
                'last_data_point': last_time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            print(f"   ✅ 评估完成: MAPE={mape:.2f}%, R2={metrics['r2_score']}")
            return metrics
            
        except Exception as e:
            print(f"   ❌ 在线评估失败: {str(e)}")
            return {'status': 'error', 'message': str(e)}


class MLService:
    """
    MLService Adapter for API compatibility.
    Wraps EnergyPredictor for regression and implements basic logic for others.
    """
    
    @staticmethod
    def train_model(
        df: pd.DataFrame,
        target_col: str,
        problem_type: str = 'regression',
        model_name: str = None,
        n_clusters: int = None
    ):
        """
        Static wrapper for API calls
        """
        if problem_type == 'regression':
            # Use EnergyPredictor
            import tempfile
            
            # Save DF to temp CSV because EnergyPredictor expects a path
            # This is a temporary workaround to avoid refactoring EnergyPredictor
            with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
                df.to_csv(tmp.name, index=False)
                tmp_path = tmp.name
            
            try:
                predictor = EnergyPredictor()
                
                # Adapt model_name
                metrics = predictor.train_model(
                    data_path=tmp_path,
                    use_firebase_storage=False,
                    target_col=target_col,
                    model_type=model_name if model_name else 'auto'
                )
                
                # EnergyPredictor.train_model sets self.pipeline
                pipeline = predictor.pipeline
                
                # Construct result
                return {
                    'pipeline': pipeline,
                    'metrics': metrics,
                    'model_type': predictor.model_type,
                    'training_samples': len(df),
                    'training_time_seconds': 0.0,
                }
            except Exception as e:
                raise MLServiceError(str(e))
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
        else:
            raise MLServiceError(f"Problem type '{problem_type}' not supported by MLService adapter yet.")

    @staticmethod
    def save_model(pipeline, storage_service, uid, model_name):
        import joblib
        import io
        
        # Save to bytes
        buffer = io.BytesIO()
        joblib.dump(pipeline, buffer)
        buffer.seek(0)
        
        # Upload
        model_filename = f"{model_name}.joblib"
        remote_path = f"models/{uid}/{model_filename}"
        
        storage_service.upload_file_obj(buffer, remote_path, content_type='application/octet-stream')
        return f"gs://{storage_service.bucket_name}/{remote_path}"

    @staticmethod
    def load_model(storage_service, model_path):
        import joblib
        import io
        
        try:
            # Download
            blob_path = model_path
            if model_path.startswith('gs://'):
                 # Extract relative path
                 parts = model_path.split('/')
                 blob_path = "/".join(parts[3:])
            
            file_bytes = storage_service.download_file(blob_path)
            buffer = io.BytesIO(file_bytes)
            model = joblib.load(buffer)
            return model
        except Exception as e:
            raise MLServiceError(f"Failed to load model: {str(e)}")

        
