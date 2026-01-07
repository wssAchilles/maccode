"""
模型评估服务 (Evaluation Service)
用于统一计算模型评估指标并生成标准化报告

功能：
1. 计算回归模型核心指标 (MAE, RMSE, MAPE, R², 置信区间)
2. 生成 Markdown 格式评估报告
3. 多模型对比分析
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import scipy.stats as stats


class EvaluationService:
    """
    模型评估服务
    
    提供统一的模型评估指标计算和报告生成功能
    """
    
    @staticmethod
    def calculate_metrics(
        y_true: np.ndarray, 
        y_pred: np.ndarray,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        计算回归模型的核心评估指标
        
        Args:
            y_true: 真实值数组
            y_pred: 预测值数组
            confidence_level: 置信水平，默认 0.95 (95%)
            
        Returns:
            包含所有指标的字典
        """
        # 确保输入是 numpy 数组
        y_true = np.asarray(y_true).flatten()
        y_pred = np.asarray(y_pred).flatten()
        
        # 基础指标
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)
        
        # MAPE (Mean Absolute Percentage Error)
        # 避免除零错误
        mask = y_true != 0
        if mask.sum() > 0:
            mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
        else:
            mape = np.nan
        
        # 残差分析
        residuals = y_true - y_pred
        residual_mean = np.mean(residuals)
        residual_std = np.std(residuals)
        
        # MAE 置信区间 (基于 Bootstrap 或正态近似)
        n = len(y_true)
        se_mae = residual_std / np.sqrt(n)  # 标准误差近似
        z_score = stats.norm.ppf((1 + confidence_level) / 2)
        mae_ci_lower = mae - z_score * se_mae
        mae_ci_upper = mae + z_score * se_mae
        
        # 预测值统计
        pred_mean = np.mean(y_pred)
        pred_std = np.std(y_pred)
        
        return {
            # 核心指标
            'mae': round(float(mae), 4),
            'rmse': round(float(rmse), 4),
            'mape': round(float(mape), 2) if not np.isnan(mape) else None,
            'r2': round(float(r2), 4),
            
            # MAE 置信区间
            'mae_ci': {
                'lower': round(float(mae_ci_lower), 4),
                'upper': round(float(mae_ci_upper), 4),
                'confidence_level': confidence_level
            },
            
            # 残差统计
            'residuals': {
                'mean': round(float(residual_mean), 4),
                'std': round(float(residual_std), 4),
                'min': round(float(np.min(residuals)), 4),
                'max': round(float(np.max(residuals)), 4)
            },
            
            # 样本信息
            'n_samples': int(n),
            'y_true_mean': round(float(np.mean(y_true)), 4),
            'y_pred_mean': round(float(pred_mean), 4)
        }
    
    @staticmethod
    def calculate_time_series_metrics(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        cv_scores: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        计算时间序列特定的评估指标
        
        Args:
            y_true: 真实值数组
            y_pred: 预测值数组
            cv_scores: 交叉验证分数列表 (可选)
            
        Returns:
            时间序列指标字典
        """
        base_metrics = EvaluationService.calculate_metrics(y_true, y_pred)
        
        # 交叉验证统计
        cv_stats = None
        if cv_scores is not None and len(cv_scores) > 0:
            cv_scores = np.asarray(cv_scores)
            cv_stats = {
                'mean': round(float(np.mean(cv_scores)), 4),
                'std': round(float(np.std(cv_scores)), 4),
                'min': round(float(np.min(cv_scores)), 4),
                'max': round(float(np.max(cv_scores)), 4),
                'n_folds': len(cv_scores)
            }
        
        base_metrics['cv_stats'] = cv_stats
        return base_metrics
    
    @staticmethod
    def compare_models(results: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """
        生成多模型对比表格
        
        Args:
            results: 字典，键为模型名称，值为 calculate_metrics 返回的指标字典
            
        Returns:
            对比表格 DataFrame
        """
        comparison_data = []
        
        for model_name, metrics in results.items():
            row = {
                'Model': model_name,
                'MAE': metrics.get('mae'),
                'RMSE': metrics.get('rmse'),
                'MAPE (%)': metrics.get('mape'),
                'R²': metrics.get('r2'),
                'MAE CI (95%)': f"[{metrics['mae_ci']['lower']:.2f}, {metrics['mae_ci']['upper']:.2f}]" 
                                if metrics.get('mae_ci') else None,
                'Samples': metrics.get('n_samples')
            }
            
            # 添加 CV 统计（如果有）
            if metrics.get('cv_stats'):
                row['CV MAE (mean±std)'] = f"{metrics['cv_stats']['mean']:.2f}±{metrics['cv_stats']['std']:.2f}"
            
            comparison_data.append(row)
        
        df = pd.DataFrame(comparison_data)
        
        # 按 MAE 排序（升序，越小越好）
        if 'MAE' in df.columns:
            df = df.sort_values('MAE', ascending=True).reset_index(drop=True)
        
        return df
    
    @staticmethod
    def generate_report(
        metrics: Dict[str, Any],
        model_info: Dict[str, Any],
        comparison_df: Optional[pd.DataFrame] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        生成 Markdown 格式的评估报告
        
        Args:
            metrics: 评估指标字典 (calculate_metrics 返回值)
            model_info: 模型信息字典，包含 name, type, hyperparameters 等
            comparison_df: 模型对比表格 (可选)
            output_path: 输出文件路径 (可选)
            
        Returns:
            Markdown 格式的报告字符串
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 构建报告
        report_lines = [
            "# 模型评估报告 (Model Evaluation Report)",
            "",
            f"> 生成时间: {timestamp}",
            "",
            "---",
            "",
            "## 1. 模型信息",
            "",
            f"| 属性 | 值 |",
            f"| :--- | :--- |",
            f"| **模型名称** | {model_info.get('name', 'Unknown')} |",
            f"| **模型类型** | {model_info.get('type', 'Unknown')} |",
            f"| **特征数量** | {model_info.get('n_features', 'N/A')} |",
            f"| **训练样本数** | {model_info.get('n_train_samples', 'N/A')} |",
            f"| **测试样本数** | {metrics.get('n_samples', 'N/A')} |",
            "",
        ]
        
        # 超参数
        if model_info.get('hyperparameters'):
            report_lines.extend([
                "### 超参数配置",
                "",
                "```json",
                str(model_info['hyperparameters']),
                "```",
                "",
            ])
        
        # 核心指标
        report_lines.extend([
            "---",
            "",
            "## 2. 核心评估指标",
            "",
            "| 指标 | 值 | 说明 |",
            "| :--- | :---: | :--- |",
            f"| **MAE** | {metrics['mae']:.4f} kW | 平均绝对误差 |",
            f"| **RMSE** | {metrics['rmse']:.4f} kW | 均方根误差 |",
            f"| **MAPE** | {metrics['mape']:.2f}% | 平均绝对百分比误差 |" if metrics.get('mape') else "| **MAPE** | N/A | 存在零值，无法计算 |",
            f"| **R²** | {metrics['r2']:.4f} | 决定系数 (解释方差比例) |",
            "",
        ])
        
        # 置信区间
        if metrics.get('mae_ci'):
            ci = metrics['mae_ci']
            report_lines.extend([
                "### MAE 置信区间",
                "",
                f"> **{int(ci['confidence_level'] * 100)}% 置信区间**: [{ci['lower']:.4f}, {ci['upper']:.4f}] kW",
                "",
            ])
        
        # 残差分析
        if metrics.get('residuals'):
            res = metrics['residuals']
            report_lines.extend([
                "---",
                "",
                "## 3. 残差分析",
                "",
                "| 统计量 | 值 |",
                "| :--- | :---: |",
                f"| 均值 | {res['mean']:.4f} |",
                f"| 标准差 | {res['std']:.4f} |",
                f"| 最小值 | {res['min']:.4f} |",
                f"| 最大值 | {res['max']:.4f} |",
                "",
            ])
        
        # CV 统计
        if metrics.get('cv_stats'):
            cv = metrics['cv_stats']
            report_lines.extend([
                "---",
                "",
                "## 4. 交叉验证结果",
                "",
                f"使用 **{cv['n_folds']} 折** 时间序列交叉验证 (TimeSeriesSplit)",
                "",
                "| 统计量 | 值 |",
                "| :--- | :---: |",
                f"| CV MAE 均值 | {cv['mean']:.4f} kW |",
                f"| CV MAE 标准差 | {cv['std']:.4f} kW |",
                f"| CV MAE 范围 | [{cv['min']:.4f}, {cv['max']:.4f}] |",
                "",
            ])
        
        # 模型对比
        if comparison_df is not None and len(comparison_df) > 0:
            report_lines.extend([
                "---",
                "",
                "## 5. 模型对比",
                "",
                comparison_df.to_markdown(index=False),
                "",
            ])
        
        # 结论
        report_lines.extend([
            "---",
            "",
            "## 结论",
            "",
            f"该模型在测试集上的 MAE 为 **{metrics['mae']:.2f} kW**，",
            f"R² 为 **{metrics['r2']:.4f}**，表明模型能够解释约 **{metrics['r2']*100:.1f}%** 的目标变量方差。",
            "",
            "---",
            "",
            "*报告由 EvaluationService 自动生成*",
        ])
        
        report = "\n".join(report_lines)
        
        # 保存到文件（如果指定了路径）
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"📄 评估报告已保存到: {output_path}")
        
        return report
    
    @staticmethod
    def calculate_improvement(baseline_mae: float, new_mae: float) -> Dict[str, float]:
        """
        计算模型改进幅度
        
        Args:
            baseline_mae: 基线模型的 MAE
            new_mae: 新模型的 MAE
            
        Returns:
            改进幅度字典
        """
        absolute_improvement = baseline_mae - new_mae
        relative_improvement = (absolute_improvement / baseline_mae) * 100 if baseline_mae > 0 else 0
        
        return {
            'absolute_improvement': round(float(absolute_improvement), 4),
            'relative_improvement_pct': round(float(relative_improvement), 2),
            'is_improved': new_mae < baseline_mae
        }


# 测试代码
if __name__ == "__main__":
    # 模拟数据测试
    np.random.seed(42)
    y_true = np.random.uniform(50, 150, 100)
    y_pred = y_true + np.random.normal(0, 5, 100)
    
    # 计算指标
    metrics = EvaluationService.calculate_metrics(y_true, y_pred)
    print("📊 评估指标:")
    for key, value in metrics.items():
        print(f"   {key}: {value}")
    
    # 生成报告
    model_info = {
        'name': 'LightGBM_Tuned',
        'type': 'LGBMRegressor',
        'n_features': 20,
        'n_train_samples': 5000,
        'hyperparameters': {'n_estimators': 300, 'learning_rate': 0.05}
    }
    
    report = EvaluationService.generate_report(metrics, model_info)
    print("\n" + report)
