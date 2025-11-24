"""
数据验证脚本 - 验证所有处理后的数据
Verification script for processed data
"""

import pandas as pd
from pathlib import Path
import sys


def verify_file(file_path: Path, expected_rows: int = None) -> bool:
    """
    验证单个文件
    
    Args:
        file_path: 文件路径
        expected_rows: 期望的行数（可选）
        
    Returns:
        验证是否通过
    """
    print(f"\n{'='*80}")
    print(f"验证文件: {file_path.name}")
    print('='*80)
    
    try:
        # 读取文件
        df = pd.read_csv(file_path, parse_dates=['Date'])
        
        # 基本信息
        print(f"✓ 文件读取成功")
        print(f"  - 行数: {len(df):,}")
        print(f"  - 列数: {len(df.columns)}")
        print(f"  - 文件大小: {file_path.stat().st_size / 1024:.1f} KB")
        
        # 检查行数
        if expected_rows:
            if len(df) == expected_rows:
                print(f"✓ 行数正确: {len(df):,} 行")
            else:
                print(f"⚠️  行数不匹配: 期望 {expected_rows:,}，实际 {len(df):,}")
        
        # 检查必需列
        required_cols = ['Date', 'Site_Load', 'Hour', 'Price', 'DayOfWeek']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"❌ 缺少必需列: {missing_cols}")
            return False
        else:
            print(f"✓ 所有必需列都存在")
        
        # 检查缺失值
        null_counts = df.isnull().sum()
        total_nulls = null_counts.sum()
        if total_nulls > 0:
            print(f"⚠️  发现缺失值:")
            for col, count in null_counts[null_counts > 0].items():
                print(f"    - {col}: {count} 个")
        else:
            print(f"✓ 无缺失值")
        
        # 检查日期范围
        print(f"✓ 日期范围: {df['Date'].min()} 到 {df['Date'].max()}")
        
        # 检查数值范围
        print(f"✓ Site_Load 范围: {df['Site_Load'].min():.2f} - {df['Site_Load'].max():.2f} kW")
        print(f"✓ Hour 范围: {df['Hour'].min()} - {df['Hour'].max()}")
        print(f"✓ DayOfWeek 范围: {df['DayOfWeek'].min()} - {df['DayOfWeek'].max()}")
        print(f"✓ Price 取值: {sorted(df['Price'].unique())}")
        
        # 检查数据类型
        if df['Date'].dtype != 'datetime64[ns]':
            print(f"⚠️  Date 列类型不正确: {df['Date'].dtype}")
        else:
            print(f"✓ Date 列类型正确: datetime64[ns]")
        
        # 显示前几行
        print(f"\n前 3 行数据:")
        print(df.head(3).to_string())
        
        print(f"\n✅ 验证通过!")
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("\n" + "🔍 " + "="*76)
    print("数据验证脚本 - 验证所有处理后的数据")
    print("="*78 + "\n")
    
    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    processed_dir = project_root / 'data' / 'processed'
    
    print(f"处理后数据目录: {processed_dir}\n")
    
    # 定义要验证的文件
    files_to_verify = [
        ('cleaned_energy_data_2018.csv', 4416),
        ('cleaned_energy_data_2019.csv', 7070),
        ('cleaned_energy_data_all.csv', 11486),
    ]
    
    results = {}
    
    # 验证每个文件
    for filename, expected_rows in files_to_verify:
        file_path = processed_dir / filename
        
        if not file_path.exists():
            print(f"\n❌ 文件不存在: {filename}")
            results[filename] = False
            continue
        
        results[filename] = verify_file(file_path, expected_rows)
    
    # 总结
    print("\n" + "="*80)
    print("验证总结")
    print("="*80)
    
    all_passed = all(results.values())
    
    for filename, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {filename}")
    
    print("\n" + "="*80)
    
    if all_passed:
        print("🎉 所有文件验证通过！数据已准备就绪，可用于模型训练。")
        return 0
    else:
        print("⚠️  部分文件验证失败，请检查上述错误信息。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
