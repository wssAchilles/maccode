"""
深度学习时序预测服务 (Deep Learning Service)
实现 LSTM/GRU 模型作为传统 ML 的对比基线

功能：
1. 创建 LSTM/GRU 模型
2. 时序数据预处理 (滑动窗口)
3. 模型训练与评估
"""

import numpy as np
import pandas as pd
from typing import Callable, Dict, List, Optional, Any, Tuple, Union
import warnings

# TensorFlow/Keras 延迟加载变量
_TENSORFLOW_AVAILABLE = None
tf = None
keras = None
layers = None

# PyTorch 延迟加载变量
_PYTORCH_AVAILABLE = None
torch = None
nn = None


class DeepLearningService:
    """
    深度学习时序预测服务
    
    支持 LSTM 和 GRU 模型进行能源负载预测
    """
    
    @staticmethod
    def _ensure_tensorflow():
        """延迟加载 TensorFlow"""
        global _TENSORFLOW_AVAILABLE, tf, keras, layers
        if _TENSORFLOW_AVAILABLE is None:
            try:
                import tensorflow as _tf
                from tensorflow import keras as _keras
                from tensorflow.keras import layers as _layers
                tf = _tf
                keras = _keras
                layers = _layers
                _TENSORFLOW_AVAILABLE = True
            except ImportError:
                _TENSORFLOW_AVAILABLE = False
                warnings.warn("TensorFlow 未安装，深度学习功能将不可用。安装命令: pip install tensorflow")
        return _TENSORFLOW_AVAILABLE

    @staticmethod
    def is_available() -> Dict[str, bool]:
        """检查深度学习框架可用性"""
        DeepLearningService._ensure_tensorflow()
        # 简单处理 PyTorch (暂不作为重点)
        global _PYTORCH_AVAILABLE, torch, nn
        if _PYTORCH_AVAILABLE is None:
            try:
                import torch as _torch
                import torch.nn as _nn
                torch = _torch
                nn = _nn
                _PYTORCH_AVAILABLE = True
            except ImportError:
                _PYTORCH_AVAILABLE = False
        
        return {
            'tensorflow': _TENSORFLOW_AVAILABLE,
            'pytorch': _PYTORCH_AVAILABLE,
            'fallback_backend': True,
            'available': True,
        }
    
    @staticmethod
    def prepare_sequences(
        df: pd.DataFrame,
        target_col: str,
        feature_cols: Optional[List[str]] = None,
        lookback: int = 24,
        horizon: int = 1
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备时序数据的滑动窗口序列
        
        Args:
            df: 输入 DataFrame (按时间排序)
            target_col: 目标列名
            feature_cols: 特征列名列表 (None 则仅使用目标列)
            lookback: 回看窗口大小 (历史步数)
            horizon: 预测步长
            
        Returns:
            X: 形状 (samples, lookback, features)
            y: 形状 (samples, horizon)
        """
        # 选择特征
        if feature_cols is None:
            feature_cols = [target_col]
        
        # 确保目标列在数据中
        if target_col not in df.columns:
            raise ValueError(f"目标列 '{target_col}' 不在 DataFrame 中")
        
        # 提取数据
        features = df[feature_cols].values
        target = df[target_col].values
        
        # 标准化 (可选，提高训练稳定性)
        # 这里返回原始数据，标准化应在模型训练前做
        
        X, y = [], []
        for i in range(len(df) - lookback - horizon + 1):
            X.append(features[i:i + lookback])
            y.append(target[i + lookback:i + lookback + horizon])
        
        return np.array(X), np.array(y)
    
    @staticmethod
    def create_lstm_model(
        input_shape: Tuple[int, int],
        units: int = 64,
        dropout: float = 0.2,
        output_size: int = 1
    ):
        """
        创建 LSTM 模型
        
        Args:
            input_shape: (lookback, features)
            units: LSTM 单元数
            dropout: Dropout 比例
            output_size: 输出维度 (预测步数)
            
        Returns:
            Keras Sequential 模型
        """
        if not DeepLearningService._ensure_tensorflow():
            raise RuntimeError("TensorFlow 未安装，无法创建 LSTM 模型")
        
        model = keras.Sequential([
            layers.LSTM(
                units, 
                return_sequences=True, 
                input_shape=input_shape
            ),
            layers.Dropout(dropout),
            layers.LSTM(units // 2, return_sequences=False),
            layers.Dropout(dropout),
            layers.Dense(32, activation='relu'),
            layers.Dense(output_size)
        ])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    @staticmethod
    def create_gru_model(
        input_shape: Tuple[int, int],
        units: int = 64,
        dropout: float = 0.2,
        output_size: int = 1
    ):
        """
        创建 GRU 模型 (比 LSTM 更快，参数更少)
        
        Args:
            input_shape: (lookback, features)
            units: GRU 单元数
            dropout: Dropout 比例
            output_size: 输出维度
            
        Returns:
            Keras Sequential 模型
        """
        if not DeepLearningService._ensure_tensorflow():
            raise RuntimeError("TensorFlow 未安装，无法创建 GRU 模型")
        
        model = keras.Sequential([
            layers.GRU(
                units, 
                return_sequences=True, 
                input_shape=input_shape
            ),
            layers.Dropout(dropout),
            layers.GRU(units // 2, return_sequences=False),
            layers.Dropout(dropout),
            layers.Dense(32, activation='relu'),
            layers.Dense(output_size)
        ])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    @staticmethod
    def train_model(
        model,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        epochs: int = 50,
        batch_size: int = 32,
        early_stopping: bool = True,
        verbose: int = 1,
        progress_callback: Optional[
            Callable[[int, int, Dict[str, float]], None]
        ] = None,
    ) -> Dict[str, Any]:
        """
        训练深度学习模型
        
        Args:
            model: Keras 模型
            X_train, y_train: 训练数据
            X_val, y_val: 验证数据 (可选)
            epochs: 训练轮数
            batch_size: 批大小
            early_stopping: 是否启用早停
            verbose: 日志级别
            
        Returns:
            训练结果字典
        """
        if not DeepLearningService._ensure_tensorflow():
            raise RuntimeError("TensorFlow 未安装")
        
        callbacks = []
        
        if early_stopping:
            callbacks.append(
                keras.callbacks.EarlyStopping(
                    monitor='val_loss' if X_val is not None else 'loss',
                    patience=10,
                    restore_best_weights=True
                )
            )
        if progress_callback is not None:
            class _EpochProgressCallback(keras.callbacks.Callback):
                def on_epoch_end(self, epoch, logs=None):
                    metrics = {
                        str(key): float(value)
                        for key, value in dict(logs or {}).items()
                        if isinstance(value, (int, float))
                    }
                    progress_callback(epoch + 1, max(int(epochs), 1), metrics)

            callbacks.append(_EpochProgressCallback())
        
        # 准备验证数据
        validation_data = None
        if X_val is not None and y_val is not None:
            validation_data = (X_val, y_val)
        
        # 训练
        history = model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=validation_data,
            callbacks=callbacks,
            verbose=verbose
        )
        
        # 评估
        train_loss, train_mae = model.evaluate(X_train, y_train, verbose=0)
        
        result = {
            'success': True,
            'epochs_trained': len(history.history['loss']),
            'train_loss': float(train_loss),
            'train_mae': float(train_mae),
            'history': {
                'loss': [float(x) for x in history.history['loss']],
                'mae': [float(x) for x in history.history['mae']]
            }
        }
        
        if validation_data:
            val_loss, val_mae = model.evaluate(X_val, y_val, verbose=0)
            result['val_loss'] = float(val_loss)
            result['val_mae'] = float(val_mae)
            result['history']['val_loss'] = [float(x) for x in history.history.get('val_loss', [])]
            result['history']['val_mae'] = [float(x) for x in history.history.get('val_mae', [])]
        
        return result
    
    @staticmethod
    def predict(model, X_new: np.ndarray) -> np.ndarray:
        """
        使用模型进行预测
        
        Args:
            model: 训练好的模型
            X_new: 新数据，形状 (samples, lookback, features)
            
        Returns:
            预测值数组
        """
        if not DeepLearningService._ensure_tensorflow():
            raise RuntimeError("TensorFlow 未安装")
        
        predictions = model.predict(X_new, verbose=0)
        return predictions.flatten()
    
    @staticmethod
    def compare_with_baseline(
        dl_predictions: np.ndarray,
        ml_predictions: np.ndarray,
        y_true: np.ndarray
    ) -> Dict[str, Any]:
        """
        比较深度学习模型与传统 ML 的性能
        
        Args:
            dl_predictions: 深度学习预测
            ml_predictions: 传统 ML 预测
            y_true: 真实值
            
        Returns:
            对比结果
        """
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        
        dl_mae = mean_absolute_error(y_true, dl_predictions)
        ml_mae = mean_absolute_error(y_true, ml_predictions)
        
        dl_rmse = np.sqrt(mean_squared_error(y_true, dl_predictions))
        ml_rmse = np.sqrt(mean_squared_error(y_true, ml_predictions))
        
        dl_r2 = r2_score(y_true, dl_predictions)
        ml_r2 = r2_score(y_true, ml_predictions)
        
        improvement = (ml_mae - dl_mae) / ml_mae * 100 if ml_mae > 0 else 0
        
        return {
            'deep_learning': {
                'mae': round(dl_mae, 4),
                'rmse': round(dl_rmse, 4),
                'r2': round(dl_r2, 4)
            },
            'traditional_ml': {
                'mae': round(ml_mae, 4),
                'rmse': round(ml_rmse, 4),
                'r2': round(ml_r2, 4)
            },
            'dl_improvement_pct': round(improvement, 2),
            'winner': 'deep_learning' if dl_mae < ml_mae else 'traditional_ml'
        }


# 测试代码
if __name__ == "__main__":
    print(f"深度学习框架可用性: {DeepLearningService.is_available()}")
    
    if TENSORFLOW_AVAILABLE:
        print("\n📊 创建测试数据...")
        np.random.seed(42)
        
        # 模拟时序数据
        n_samples = 1000
        t = np.arange(n_samples)
        data = 100 + 20 * np.sin(2 * np.pi * t / 24) + np.random.randn(n_samples) * 5
        
        df = pd.DataFrame({
            'Date': pd.date_range('2023-01-01', periods=n_samples, freq='H'),
            'Site_Load': data
        })
        
        # 准备序列
        X, y = DeepLearningService.prepare_sequences(
            df, target_col='Site_Load', lookback=24
        )
        print(f"X 形状: {X.shape}, y 形状: {y.shape}")
        
        # 划分数据
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        # 创建模型
        print("\n🏗️ 创建 LSTM 模型...")
        model = DeepLearningService.create_lstm_model(
            input_shape=(24, 1),
            units=32
        )
        print(model.summary())
        
        # 快速训练测试
        print("\n🚀 训练模型 (5 轮)...")
        result = DeepLearningService.train_model(
            model, X_train, y_train,
            X_val=X_test, y_val=y_test,
            epochs=5, verbose=1
        )
        print(f"训练 MAE: {result['train_mae']:.4f}")
        if 'val_mae' in result:
            print(f"验证 MAE: {result['val_mae']:.4f}")
