"""
测试数据处理器模块
Test script for data_processor module
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.data_processor import preprocess_energy_data
import pandas as pd


def test_basic_usage():
    """测试基本用法"""
    print("=" * 80)
    print("测试 1: 基本用法 - 使用默认参数")
    print("=" * 80)
    
    # 使用默认参数
    df = preprocess_energy_data()
    
    # 验证结果
    assert df is not None, "返回的 DataFrame 不应为 None"
    assert len(df) > 0, "DataFrame 不应为空"
    assert 'Site_Load' in df.columns, "应包含 Site_Load 列"
    assert 'Price' in df.columns, "应包含 Price 列"
    assert 'Hour' in df.columns, "应包含 Hour 列"
    assert 'DayOfWeek' in df.columns, "应包含 DayOfWeek 列"
    
    print("\n✅ 测试通过！\n")


def test_custom_output():
    """测试自定义输出文件名"""
    print("=" * 80)
    print("测试 2: 自定义输出文件名")
    print("=" * 80)
    
    # 使用自定义输出文件名
    df = preprocess_energy_data(output_file='test_output.csv')
    
    print("\n✅ 测试通过！自定义文件已保存为 test_output.csv\n")


def test_data_quality():
    """测试数据质量"""
    print("=" * 80)
    print("测试 3: 数据质量检查")
    print("=" * 80)
    
    df = preprocess_energy_data()
    
    # 检查是否有缺失值
    missing_values = df.isnull().sum()
    print("\n缺失值统计:")
    print(missing_values)
    
    # 检查电价是否在合理范围内
    assert df['Price'].min() >= 0.3, "电价最小值应为 0.3"
    assert df['Price'].max() <= 1.0, "电价最大值应为 1.0"
    
    # 检查小时是否在 0-23 范围内
    assert df['Hour'].min() >= 0, "小时最小值应为 0"
    assert df['Hour'].max() <= 23, "小时最大值应为 23"
    
    # 检查星期几是否在 0-6 范围内
    assert df['DayOfWeek'].min() >= 0, "星期几最小值应为 0"
    assert df['DayOfWeek'].max() <= 6, "星期几最大值应为 6"
    
    print("\n✅ 数据质量检查通过！\n")


def analyze_price_distribution():
    """分析电价分布"""
    print("=" * 80)
    print("分析: 电价分布统计")
    print("=" * 80)
    
    df = preprocess_energy_data()
    
    price_counts = df['Price'].value_counts().sort_index()
    print("\n电价分布:")
    for price, count in price_counts.items():
        percentage = (count / len(df)) * 100
        print(f"  {price} 元/kWh: {count} 小时 ({percentage:.1f}%)")
    
    print("\n")


if __name__ == '__main__':
    """运行所有测试"""
    print("\n🧪 开始运行数据处理器测试套件...\n")
    
    # 运行测试
    test_basic_usage()
    test_data_quality()
    analyze_price_distribution()
    
    print("🎉 所有测试完成！\n")
