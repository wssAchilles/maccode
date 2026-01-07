"""
数据漂移检测服务 (Data Drift Detection Service)
检测训练数据与推理数据的分布变化

功能：
1. 计算 PSI (Population Stability Index)
2. 多特征漂移检测
3. 生成漂移报告
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime


class DriftService:
    """
    数据漂移检测服务
    
    使用 PSI (Population Stability Index) 检测数据分布变化
    
    PSI 阈值解读:
    - PSI < 0.1: 无显著漂移 (稳定)
    - 0.1 ≤ PSI < 0.2: 轻微漂移 (需关注)
    - PSI ≥ 0.2: 显著漂移 (需要重新训练)
    """
    
    # 漂移阈值
    THRESHOLD_STABLE = 0.1
    THRESHOLD_WARNING = 0.2
    
    @staticmethod
    def calculate_psi(
        expected: np.ndarray,
        actual: np.ndarray,
        buckets: int = 10,
        eps: float = 1e-6
    ) -> float:
        """
        计算 Population Stability Index (PSI)
        
        PSI = Σ (actual% - expected%) * ln(actual% / expected%)
        
        Args:
            expected: 训练数据分布 (基准)
            actual: 推理/当前数据分布
            buckets: 分箱数量
            eps: 避免除零的小值
            
        Returns:
            PSI 值
        """
        # 转换为 numpy 数组并展平
        expected = np.asarray(expected).flatten()
        actual = np.asarray(actual).flatten()
        
        # 移除 NaN
        expected = expected[~np.isnan(expected)]
        actual = actual[~np.isnan(actual)]
        
        if len(expected) == 0 or len(actual) == 0:
            return 0.0
        
        # 计算分位数边界 (基于 expected 数据)
        breakpoints = np.percentile(expected, np.linspace(0, 100, buckets + 1))
        breakpoints = np.unique(breakpoints)  # 移除重复边界
        
        if len(breakpoints) < 2:
            return 0.0
        
        # 计算每个桶的占比
        expected_counts, _ = np.histogram(expected, bins=breakpoints)
        actual_counts, _ = np.histogram(actual, bins=breakpoints)
        
        # 转为占比
        expected_pct = expected_counts / len(expected) + eps
        actual_pct = actual_counts / len(actual) + eps
        
        # 计算 PSI
        psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
        
        return float(psi)
    
    @staticmethod
    def calculate_kl_divergence(
        p: np.ndarray,
        q: np.ndarray,
        buckets: int = 10,
        eps: float = 1e-6
    ) -> float:
        """
        计算 KL 散度 (Kullback-Leibler Divergence)
        
        KL(P || Q) = Σ P(x) * log(P(x) / Q(x))
        
        Args:
            p: 分布 P (通常是训练数据)
            q: 分布 Q (通常是推理数据)
            buckets: 分箱数量
            eps: 避免除零
            
        Returns:
            KL 散度值
        """
        p = np.asarray(p).flatten()
        q = np.asarray(q).flatten()
        
        # 移除 NaN
        p = p[~np.isnan(p)]
        q = q[~np.isnan(q)]
        
        if len(p) == 0 or len(q) == 0:
            return 0.0
        
        # 计算直方图
        min_val = min(p.min(), q.min())
        max_val = max(p.max(), q.max())
        
        bins = np.linspace(min_val, max_val, buckets + 1)
        
        p_hist, _ = np.histogram(p, bins=bins, density=True)
        q_hist, _ = np.histogram(q, bins=bins, density=True)
        
        # 添加 eps 避免除零
        p_hist = p_hist + eps
        q_hist = q_hist + eps
        
        # 归一化
        p_hist = p_hist / p_hist.sum()
        q_hist = q_hist / q_hist.sum()
        
        # KL 散度
        kl = np.sum(p_hist * np.log(p_hist / q_hist))
        
        return float(kl)
    
    @staticmethod
    def get_drift_status(psi: float) -> str:
        """
        根据 PSI 值返回漂移状态
        
        Args:
            psi: PSI 值
            
        Returns:
            漂移状态字符串
        """
        if psi < DriftService.THRESHOLD_STABLE:
            return "stable"  # 稳定
        elif psi < DriftService.THRESHOLD_WARNING:
            return "warning"  # 警告
        else:
            return "drift"  # 显著漂移
    
    @staticmethod
    def detect_feature_drift(
        train_df: pd.DataFrame,
        serving_df: pd.DataFrame,
        features: Optional[List[str]] = None,
        threshold: float = 0.2
    ) -> Dict[str, Any]:
        """
        检测多个特征的数据漂移
        
        Args:
            train_df: 训练数据 DataFrame
            serving_df: 推理/当前数据 DataFrame
            features: 要检测的特征列表 (None 则检测所有数值列)
            threshold: 漂移阈值
            
        Returns:
            漂移检测结果字典
        """
        if features is None:
            # 自动选择数值列
            numeric_cols = train_df.select_dtypes(include=[np.number]).columns
            features = [col for col in numeric_cols if col in serving_df.columns]
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'n_features': len(features),
            'threshold': threshold,
            'features': {},
            'summary': {
                'stable': 0,
                'warning': 0,
                'drift': 0
            }
        }
        
        drifted_features = []
        warning_features = []
        
        for feature in features:
            if feature not in train_df.columns or feature not in serving_df.columns:
                continue
            
            train_values = train_df[feature].dropna().values
            serving_values = serving_df[feature].dropna().values
            
            if len(train_values) == 0 or len(serving_values) == 0:
                continue
            
            # 计算 PSI
            psi = DriftService.calculate_psi(train_values, serving_values)
            status = DriftService.get_drift_status(psi)
            
            # 计算基本统计
            train_stats = {
                'mean': float(np.mean(train_values)),
                'std': float(np.std(train_values)),
                'min': float(np.min(train_values)),
                'max': float(np.max(train_values))
            }
            
            serving_stats = {
                'mean': float(np.mean(serving_values)),
                'std': float(np.std(serving_values)),
                'min': float(np.min(serving_values)),
                'max': float(np.max(serving_values))
            }
            
            results['features'][feature] = {
                'psi': round(psi, 4),
                'status': status,
                'train_stats': train_stats,
                'serving_stats': serving_stats,
                'mean_shift': round(serving_stats['mean'] - train_stats['mean'], 4),
                'std_ratio': round(serving_stats['std'] / train_stats['std'], 4) if train_stats['std'] > 0 else None
            }
            
            # 更新汇总
            results['summary'][status] += 1
            
            if status == 'drift':
                drifted_features.append((feature, psi))
            elif status == 'warning':
                warning_features.append((feature, psi))
        
        # 排序并记录
        results['drifted_features'] = sorted(drifted_features, key=lambda x: x[1], reverse=True)
        results['warning_features'] = sorted(warning_features, key=lambda x: x[1], reverse=True)
        
        # 整体状态
        if results['summary']['drift'] > 0:
            results['overall_status'] = 'drift'
            results['recommendation'] = '检测到显著漂移，建议重新训练模型'
        elif results['summary']['warning'] > 0:
            results['overall_status'] = 'warning'
            results['recommendation'] = '存在轻微漂移，建议持续监控'
        else:
            results['overall_status'] = 'stable'
            results['recommendation'] = '数据分布稳定，模型可继续使用'
        
        return results
    
    @staticmethod
    def generate_drift_report(drift_results: Dict[str, Any]) -> str:
        """
        生成漂移检测报告 (Markdown 格式)
        
        Args:
            drift_results: detect_feature_drift 的返回结果
            
        Returns:
            Markdown 格式报告
        """
        lines = [
            "# 数据漂移检测报告",
            "",
            f"> 检测时间: {drift_results.get('timestamp', 'N/A')}",
            "",
        ]
        
        # 整体状态
        overall = drift_results.get('overall_status', 'unknown')
        status_emoji = {'stable': '✅', 'warning': '⚠️', 'drift': '🚨'}.get(overall, '❓')
        
        lines.extend([
            f"## 整体状态: {status_emoji} {overall.upper()}",
            "",
            f"**建议**: {drift_results.get('recommendation', 'N/A')}",
            "",
            "---",
            "",
            "## 检测汇总",
            "",
            "| 状态 | 特征数 |",
            "| :--- | :---: |",
            f"| 🟢 稳定 (PSI < 0.1) | {drift_results['summary']['stable']} |",
            f"| 🟡 警告 (0.1 ≤ PSI < 0.2) | {drift_results['summary']['warning']} |",
            f"| 🔴 漂移 (PSI ≥ 0.2) | {drift_results['summary']['drift']} |",
            "",
        ])
        
        # 漂移特征详情
        if drift_results.get('drifted_features'):
            lines.extend([
                "---",
                "",
                "## 显著漂移特征",
                "",
                "| 特征 | PSI | 均值偏移 |",
                "| :--- | :---: | :---: |",
            ])
            for feat, psi in drift_results['drifted_features']:
                feat_info = drift_results['features'].get(feat, {})
                mean_shift = feat_info.get('mean_shift', 'N/A')
                lines.append(f"| {feat} | {psi:.4f} | {mean_shift} |")
            lines.append("")
        
        # 警告特征
        if drift_results.get('warning_features'):
            lines.extend([
                "---",
                "",
                "## 轻微漂移特征 (需关注)",
                "",
                "| 特征 | PSI |",
                "| :--- | :---: |",
            ])
            for feat, psi in drift_results['warning_features']:
                lines.append(f"| {feat} | {psi:.4f} |")
            lines.append("")
        
        lines.extend([
            "---",
            "",
            "*报告由 DriftService 自动生成*"
        ])
        
        return "\n".join(lines)
    
    @staticmethod
    def quick_check(
        train_values: np.ndarray,
        serving_values: np.ndarray
    ) -> Dict[str, Any]:
        """
        快速检测单个特征的漂移
        
        Args:
            train_values: 训练数据值
            serving_values: 推理数据值
            
        Returns:
            快速检测结果
        """
        psi = DriftService.calculate_psi(train_values, serving_values)
        status = DriftService.get_drift_status(psi)
        
        return {
            'psi': round(psi, 4),
            'status': status,
            'needs_retrain': status == 'drift'
        }


# 测试代码
if __name__ == "__main__":
    np.random.seed(42)
    
    # 模拟训练数据
    train_data = np.random.normal(100, 15, 1000)
    
    # 模拟推理数据 (有漂移)
    serving_data_stable = np.random.normal(100, 15, 500)  # 无漂移
    serving_data_drift = np.random.normal(120, 20, 500)  # 显著漂移
    
    print("📊 PSI 漂移检测测试")
    print("-" * 40)
    
    # 稳定场景
    psi_stable = DriftService.calculate_psi(train_data, serving_data_stable)
    status_stable = DriftService.get_drift_status(psi_stable)
    print(f"稳定场景: PSI={psi_stable:.4f}, 状态={status_stable}")
    
    # 漂移场景
    psi_drift = DriftService.calculate_psi(train_data, serving_data_drift)
    status_drift = DriftService.get_drift_status(psi_drift)
    print(f"漂移场景: PSI={psi_drift:.4f}, 状态={status_drift}")
    
    # 多特征检测
    print("\n📋 多特征漂移检测")
    train_df = pd.DataFrame({
        'feature_A': np.random.normal(100, 15, 1000),
        'feature_B': np.random.normal(50, 10, 1000),
        'feature_C': np.random.uniform(0, 100, 1000)
    })
    
    serving_df = pd.DataFrame({
        'feature_A': np.random.normal(100, 15, 500),  # 稳定
        'feature_B': np.random.normal(60, 15, 500),   # 轻微漂移
        'feature_C': np.random.uniform(20, 120, 500)  # 可能漂移
    })
    
    results = DriftService.detect_feature_drift(train_df, serving_df)
    print(f"整体状态: {results['overall_status']}")
    print(f"稳定特征: {results['summary']['stable']}, 警告: {results['summary']['warning']}, 漂移: {results['summary']['drift']}")
