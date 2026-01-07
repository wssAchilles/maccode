"""
模型可解释性服务 (Explainability Service)
使用 SHAP (SHapley Additive exPlanations) 解释模型预测

功能：
1. 计算 SHAP 值
2. 提取 Top N 重要特征
3. 生成 SHAP summary plot
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Union
import warnings
import io
import base64

# SHAP 可能未安装
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    warnings.warn("SHAP 未安装，可解释性功能将不可用")


class ExplainabilityService:
    """
    模型可解释性服务
    
    提供基于 SHAP 的模型解释功能
    """
    
    @staticmethod
    def is_available() -> bool:
        """检查 SHAP 是否可用"""
        return SHAP_AVAILABLE
    
    @staticmethod
    def compute_shap_values(
        model,
        X_sample: Union[pd.DataFrame, np.ndarray],
        feature_names: Optional[List[str]] = None,
        max_samples: int = 100,
        use_tree_explainer: bool = True
    ) -> Dict[str, Any]:
        """
        计算 SHAP 值
        
        Args:
            model: 训练好的模型 (支持 tree-based 和通用模型)
            X_sample: 用于计算 SHAP 的样本数据
            feature_names: 特征名列表
            max_samples: 最大采样数量 (控制计算时间)
            use_tree_explainer: 是否优先使用 TreeExplainer (更快)
            
        Returns:
            包含 SHAP 值和相关信息的字典
        """
        if not SHAP_AVAILABLE:
            return {
                'success': False,
                'error': 'SHAP 未安装',
                'shap_values': None
            }
        
        try:
            # 转换为 DataFrame (如果是 numpy array)
            if isinstance(X_sample, np.ndarray):
                if feature_names:
                    X_sample = pd.DataFrame(X_sample, columns=feature_names)
                else:
                    X_sample = pd.DataFrame(X_sample)
            
            # 采样 (避免计算时间过长)
            if len(X_sample) > max_samples:
                X_sample = X_sample.sample(n=max_samples, random_state=42)
            
            # 选择合适的 Explainer
            explainer = None
            shap_values = None
            explainer_type = None
            
            # 检查模型类型选择 Explainer
            model_type = type(model).__name__.lower()
            
            if use_tree_explainer and any(t in model_type for t in ['forest', 'gbm', 'lgbm', 'xgb', 'gradient']):
                try:
                    # TreeExplainer (快速，适用于树模型)
                    explainer = shap.TreeExplainer(model)
                    shap_values = explainer.shap_values(X_sample)
                    explainer_type = 'TreeExplainer'
                except Exception:
                    pass
            
            if explainer is None:
                # 回退到 KernelExplainer (通用但较慢)
                # 使用背景数据的子集
                background = shap.sample(X_sample, min(50, len(X_sample)))
                explainer = shap.KernelExplainer(model.predict, background)
                shap_values = explainer.shap_values(X_sample)
                explainer_type = 'KernelExplainer'
            
            # 获取特征名
            if feature_names is None:
                feature_names = list(X_sample.columns) if hasattr(X_sample, 'columns') else [f'f{i}' for i in range(X_sample.shape[1])]
            
            # 计算平均绝对 SHAP 值 (特征重要性)
            if isinstance(shap_values, list):
                # 多输出模型
                mean_abs_shap = np.mean([np.abs(sv).mean(axis=0) for sv in shap_values], axis=0)
            else:
                mean_abs_shap = np.abs(shap_values).mean(axis=0)
            
            # 构建特征重要性排序
            feature_importance = sorted(
                zip(feature_names, mean_abs_shap),
                key=lambda x: x[1],
                reverse=True
            )
            
            return {
                'success': True,
                'shap_values': shap_values,
                'expected_value': explainer.expected_value if hasattr(explainer, 'expected_value') else None,
                'feature_names': feature_names,
                'feature_importance': feature_importance,
                'explainer_type': explainer_type,
                'n_samples': len(X_sample)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'shap_values': None
            }
    
    @staticmethod
    def get_top_features(
        shap_result: Dict[str, Any],
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取 Top N 重要特征
        
        Args:
            shap_result: compute_shap_values 的返回结果
            top_n: 返回的特征数量
            
        Returns:
            Top N 特征列表，包含名称和重要性分数
        """
        if not shap_result.get('success') or not shap_result.get('feature_importance'):
            return []
        
        feature_importance = shap_result['feature_importance'][:top_n]
        
        # 归一化为百分比
        total_importance = sum(imp for _, imp in feature_importance)
        
        return [
            {
                'feature': name,
                'importance': round(float(imp), 4),
                'importance_pct': round(float(imp / total_importance * 100), 2) if total_importance > 0 else 0,
                'rank': i + 1
            }
            for i, (name, imp) in enumerate(feature_importance)
        ]
    
    @staticmethod
    def generate_summary_plot(
        shap_result: Dict[str, Any],
        X_sample: Union[pd.DataFrame, np.ndarray],
        output_path: Optional[str] = None,
        plot_type: str = 'bar',
        max_display: int = 15
    ) -> Optional[str]:
        """
        生成 SHAP summary plot
        
        Args:
            shap_result: compute_shap_values 的返回结果
            X_sample: 样本数据 (用于 beeswarm 图)
            output_path: 输出文件路径 (None 则返回 base64)
            plot_type: 图表类型 ('bar', 'beeswarm', 'dot')
            max_display: 最大显示特征数
            
        Returns:
            图表文件路径或 base64 编码字符串
        """
        if not SHAP_AVAILABLE:
            return None
        
        if not shap_result.get('success'):
            return None
        
        try:
            import matplotlib
            matplotlib.use('Agg')  # 非交互式后端
            import matplotlib.pyplot as plt
            
            shap_values = shap_result['shap_values']
            feature_names = shap_result.get('feature_names')
            
            # 确保 X_sample 是 DataFrame
            if isinstance(X_sample, np.ndarray) and feature_names:
                X_sample = pd.DataFrame(X_sample, columns=feature_names)
            
            # 创建图表
            plt.figure(figsize=(10, 8))
            
            if plot_type == 'bar':
                # 条形图 (平均绝对 SHAP 值)
                shap.summary_plot(
                    shap_values, 
                    X_sample,
                    plot_type='bar',
                    max_display=max_display,
                    show=False
                )
            elif plot_type == 'beeswarm' or plot_type == 'dot':
                # 蜂巢图 (显示特征值与 SHAP 值关系)
                shap.summary_plot(
                    shap_values,
                    X_sample,
                    max_display=max_display,
                    show=False
                )
            
            plt.title('SHAP Feature Importance', fontsize=14)
            plt.tight_layout()
            
            if output_path:
                plt.savefig(output_path, dpi=150, bbox_inches='tight')
                plt.close()
                return output_path
            else:
                # 返回 base64 编码
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                plt.close()
                buf.seek(0)
                img_base64 = base64.b64encode(buf.read()).decode('utf-8')
                return f"data:image/png;base64,{img_base64}"
                
        except Exception as e:
            print(f"生成 SHAP 图表失败: {e}")
            return None
    
    @staticmethod
    def explain_single_prediction(
        model,
        X_single: Union[pd.DataFrame, np.ndarray],
        X_background: Union[pd.DataFrame, np.ndarray],
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        解释单个预测
        
        Args:
            model: 训练好的模型
            X_single: 待解释的单个样本
            X_background: 背景数据 (用于对比)
            feature_names: 特征名列表
            
        Returns:
            单个预测的 SHAP 解释
        """
        if not SHAP_AVAILABLE:
            return {'success': False, 'error': 'SHAP 未安装'}
        
        try:
            # 确保是 2D
            if X_single.ndim == 1:
                X_single = X_single.reshape(1, -1)
            
            # 计算 SHAP
            result = ExplainabilityService.compute_shap_values(
                model, X_single, feature_names, max_samples=1, use_tree_explainer=True
            )
            
            if not result['success']:
                return result
            
            shap_values = result['shap_values']
            
            # 单样本的 SHAP 值
            if isinstance(shap_values, np.ndarray):
                single_shap = shap_values[0] if shap_values.ndim > 1 else shap_values
            else:
                single_shap = shap_values[0][0]
            
            # 获取预测值
            prediction = float(model.predict(X_single)[0])
            base_value = result.get('expected_value', prediction)
            if isinstance(base_value, np.ndarray):
                base_value = float(base_value[0]) if len(base_value) > 0 else float(base_value)
            
            # 构建特征贡献
            contributions = []
            for i, (name, value) in enumerate(zip(feature_names or [f'f{i}' for i in range(len(single_shap))], single_shap)):
                contributions.append({
                    'feature': name,
                    'contribution': round(float(value), 4),
                    'direction': 'positive' if value > 0 else 'negative'
                })
            
            # 按贡献绝对值排序
            contributions.sort(key=lambda x: abs(x['contribution']), reverse=True)
            
            return {
                'success': True,
                'prediction': round(prediction, 4),
                'base_value': round(float(base_value), 4) if base_value else None,
                'contributions': contributions,
                'top_positive': [c for c in contributions if c['direction'] == 'positive'][:5],
                'top_negative': [c for c in contributions if c['direction'] == 'negative'][:5]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}


# 测试代码
if __name__ == "__main__":
    print(f"SHAP 可用: {SHAP_AVAILABLE}")
    
    if SHAP_AVAILABLE:
        # 简单测试
        from sklearn.ensemble import RandomForestRegressor
        
        # 创建模拟数据
        np.random.seed(42)
        X = np.random.randn(100, 5)
        y = X[:, 0] * 2 + X[:, 1] * 1.5 + np.random.randn(100) * 0.1
        
        # 训练模型
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        model.fit(X, y)
        
        # 计算 SHAP
        feature_names = ['A', 'B', 'C', 'D', 'E']
        result = ExplainabilityService.compute_shap_values(model, X, feature_names)
        
        print(f"SHAP 计算成功: {result['success']}")
        print(f"Explainer 类型: {result.get('explainer_type')}")
        
        # Top 特征
        top_features = ExplainabilityService.get_top_features(result, top_n=5)
        print("\nTop 5 特征:")
        for feat in top_features:
            print(f"  {feat['rank']}. {feat['feature']}: {feat['importance_pct']}%")
