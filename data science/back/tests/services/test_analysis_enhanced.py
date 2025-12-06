"""
测试增强的数据分析功能
Phase 1: 数据质量评估
Phase 2: 统计分析与相关性
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import numpy as np
from services.analysis_service import AnalysisService


def test_quality_check():
    """测试数据质量检查功能"""
    print("=" * 60)
    print("测试 Phase 1: 数据质量评估")
    print("=" * 60)
    
    # 创建测试数据
    np.random.seed(42)
    n_rows = 100
    
    data = {
        'age': np.random.normal(30, 10, n_rows),
        'income': np.random.exponential(50000, n_rows),
        'score': np.random.uniform(0, 100, n_rows),
        'category': np.random.choice(['A', 'B', 'C'], n_rows),
    }
    
    df = pd.DataFrame(data)
    
    # 添加缺失值
    df.loc[0:10, 'income'] = np.nan  # 11% missing
    
    # 添加异常值
    df.loc[95:99, 'age'] = [150, 200, -50, 180, 160]
    
    # 添加重复行
    df = pd.concat([df, df.iloc[0:5]], ignore_index=True)
    
    print(f"\n测试数据集: {df.shape[0]} 行 x {df.shape[1]} 列")
    
    # 执行质量检查
    result = AnalysisService.perform_quality_check(df)
    
    if result['success']:
        print(f"\n✓ 质量分数: {result['quality_score']}/100")
        print(f"\n质量指标:")
        print(f"  - 总缺失值: {result['quality_metrics']['total_missing']}")
        print(f"  - 缺失率: {result['quality_metrics']['missing_rate']}%")
        print(f"  - 异常值数量: {result['quality_metrics']['total_outliers']}")
        print(f"  - 重复行: {result['quality_metrics']['duplicate_rows']}")
        
        print(f"\n高风险列 (缺失率>5%): {result['high_risk_columns']}")
        
        print(f"\n异常值检测:")
        for col, info in result['outlier_detection'].items():
            if 'error' not in info:
                print(f"  - {col}: {info['count']} 个异常值 ({info['percentage']:.2f}%)")
        
        print(f"\n数据摘要 (数值列):")
        for col, stats in result['data_summary']['numeric_columns'].items():
            if 'error' not in stats:
                print(f"  - {col}: 偏度={stats['skewness']:.2f}, 峰度={stats['kurtosis']:.2f}")
        
        print(f"\n建议:")
        for i, rec in enumerate(result['recommendations'], 1):
            print(f"  {i}. {rec}")
    else:
        print(f"\n✗ 错误: {result.get('message', 'Unknown error')}")


def test_correlations():
    """测试相关性分析功能"""
    print("\n" + "=" * 60)
    print("测试 Phase 2: 相关性分析")
    print("=" * 60)
    
    # 创建测试数据（带强相关性）
    np.random.seed(42)
    n_rows = 100
    
    x1 = np.random.normal(50, 10, n_rows)
    x2 = x1 + np.random.normal(0, 2, n_rows)  # 高度相关
    x3 = np.random.normal(30, 5, n_rows)  # 独立
    
    df = pd.DataFrame({
        'variable_A': x1,
        'variable_B': x2,
        'variable_C': x3,
    })
    
    print(f"\n测试数据集: {df.shape[0]} 行 x {df.shape[1]} 列")
    
    # 执行相关性分析
    result = AnalysisService.calculate_correlations(df)
    
    if result['success']:
        print(f"\n✓ 找到 {len(result['correlations'])} 对变量相关性")
        
        print(f"\n详细相关性:")
        for corr in result['correlations']:
            if 'error' not in corr:
                print(f"\n  {corr['variable_x']} vs {corr['variable_y']}:")
                print(f"    Pearson: r={corr['pearson']['correlation']:.4f}, p={corr['pearson']['p_value']:.6f}")
                print(f"    Spearman: r={corr['spearman']['correlation']:.4f}, p={corr['spearman']['p_value']:.6f}")
        
        print(f"\n高度相关变量对 (|r|>0.7):")
        for hc in result['high_correlations']:
            print(f"  - {hc['variables'][0]} & {hc['variables'][1]}: r={hc['correlation']:.4f} ({hc['type']})")
        
        print(f"\n建议:")
        for i, sug in enumerate(result['suggestions'], 1):
            print(f"  {i}. {sug}")
    else:
        print(f"\n✗ 错误: {result.get('message', 'Unknown error')}")


def test_statistical_tests():
    """测试统计检验功能"""
    print("\n" + "=" * 60)
    print("测试 Phase 2: 统计检验")
    print("=" * 60)
    
    # 创建测试数据（正态和非正态）
    np.random.seed(42)
    n_rows = 100
    
    df = pd.DataFrame({
        'normal_dist': np.random.normal(50, 10, n_rows),
        'exponential_dist': np.random.exponential(5, n_rows),
        'uniform_dist': np.random.uniform(0, 100, n_rows),
    })
    
    print(f"\n测试数据集: {df.shape[0]} 行 x {df.shape[1]} 列")
    
    # 执行统计检验
    result = AnalysisService.perform_statistical_tests(df)
    
    if result['success']:
        print(f"\n✓ 检验了 {result['summary']['total_numeric_columns']} 个数值列")
        print(f"  - 正态分布: {result['summary']['normal_distribution_count']}")
        print(f"  - 非正态分布: {result['summary']['non_normal_distribution_count']}")
        
        print(f"\n详细检验结果:")
        for col, test in result['normality_tests'].items():
            if 'error' not in test:
                print(f"\n  {col}:")
                print(f"    检验方法: {test['test_name']}")
                print(f"    p-value: {test['p_value']:.6f}")
                print(f"    结果: {test['distribution']}")
                print(f"    偏度: {test['skewness']:.4f}")
                print(f"    峰度: {test['kurtosis']:.4f}")
        
        print(f"\n非正态分布列: {result['non_normal_columns']}")
        
        print(f"\n建议:")
        for i, sug in enumerate(result['suggestions'], 1):
            print(f"  {i}. {sug}")
    else:
        print(f"\n✗ 错误: {result.get('message', 'Unknown error')}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("增强数据分析服务测试")
    print("Week 03, 04, 05, 13 课程功能")
    print("=" * 60)
    
    try:
        test_quality_check()
        test_correlations()
        test_statistical_tests()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试完成")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
