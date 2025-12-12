"""
数据预处理模块 - 家庭微网能源优化系统
Data Preprocessing Module for Home Microgrid Energy Optimization System

作者: 资深数据工程师
功能: 完整的 ETL 流程，包括数据读取、特征聚合、合并、重采样和特征工程
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, List
import warnings
from datetime import datetime

# 美国节假日库（支持加州）
try:
    import holidays
    # 创建加州节假日实例（包含联邦节假日 + 加州州立节假日）
    US_CA_HOLIDAYS = holidays.US(state='CA')
    HOLIDAYS_AVAILABLE = True
except ImportError:
    HOLIDAYS_AVAILABLE = False
    US_CA_HOLIDAYS = None
    print("⚠️ holidays 未安装，将使用简化节假日判断")

warnings.filterwarnings('ignore')

# 确保能导入 config (如果直接运行脚本)
import sys
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config


class EnergyDataProcessor:
    """
    能源数据处理器类
    负责处理分钟级能耗数据，转换为小时级训练数据
    """
    
    def __init__(self, raw_data_dir: str = None, output_dir: str = None):
        """
        初始化数据处理器
        
        Args:
            raw_data_dir: 原始数据目录路径
            output_dir: 输出数据目录路径
        """
        # 获取项目根目录（back/services 的上两级）
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent.parent
        
        # 设置数据路径
        self.raw_data_dir = Path(raw_data_dir) if raw_data_dir else self.project_root / 'data' / 'raw'
        self.output_dir = Path(output_dir) if output_dir else self.project_root / 'data' / 'processed'
        
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 原始数据目录: {self.raw_data_dir}")
        print(f"📁 输出数据目录: {self.output_dir}")
    
    def read_csv_with_date(self, file_path: Path) -> pd.DataFrame:
        """
        读取 CSV 文件并解析日期列
        
        Args:
            file_path: CSV 文件路径
            
        Returns:
            解析后的 DataFrame
        """
        print(f"📖 正在读取: {file_path.name}")
        df = pd.read_csv(file_path, parse_dates=['Date'])
        print(f"   ✓ 读取完成，共 {len(df)} 行数据")
        return df
    
    def aggregate_power_columns(self, df: pd.DataFrame, floor_name: str) -> pd.DataFrame:
        """
        聚合所有功率列（包含 'kW' 的列）
        
        Args:
            df: 输入 DataFrame
            floor_name: 楼层名称（用于生成列名）
            
        Returns:
            添加了总负载列的 DataFrame
        """
        # 自动识别所有包含 'kW' 的列
        power_columns = [col for col in df.columns if 'kW' in col]
        
        if not power_columns:
            raise ValueError(f"在 {floor_name} 数据中未找到包含 'kW' 的功率列")
        
        print(f"🔌 {floor_name} 发现 {len(power_columns)} 个功率列")
        
        # 计算总负载
        total_load_col = f'Total_Load_{floor_name}'
        df[total_load_col] = df[power_columns].sum(axis=1)
        
        print(f"   ✓ 已生成 {total_load_col}，范围: {df[total_load_col].min():.2f} - {df[total_load_col].max():.2f} kW")
        
        return df
    
    def extract_temperature(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        提取温度列（包含 'degC' 的列）
        
        Args:
            df: 输入 DataFrame
            
        Returns:
            添加了温度列的 DataFrame
        """
        # 自动识别所有包含 'degC' 的列
        temp_columns = [col for col in df.columns if 'degC' in col]
        
        if not temp_columns:
            raise ValueError("未找到包含 'degC' 的温度列")
        
        print(f"🌡️  发现 {len(temp_columns)} 个温度列")
        
        # 如果有多个温度列，取平均值
        if len(temp_columns) > 1:
            df['Temperature'] = df[temp_columns].mean(axis=1)
            print(f"   ✓ 已对多个温度列取平均值生成 Temperature")
        else:
            df['Temperature'] = df[temp_columns[0]]
            print(f"   ✓ 已提取温度列: {temp_columns[0]} -> Temperature")
        
        return df
    
    def merge_floors(self, df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
        """
        合并两个楼层的数据
        
        Args:
            df1: Floor1 数据
            df2: Floor2 数据
            
        Returns:
            合并后的 DataFrame
        """
        print("🔗 正在合并两个楼层的数据...")
        
        # 选择需要的列进行合并
        df1_subset = df1[['Date', 'Total_Load_F1']].copy()
        df2_subset = df2[['Date', 'Total_Load_F2', 'Temperature']].copy()
        
        # 内连接
        merged_df = pd.merge(df1_subset, df2_subset, on='Date', how='inner')
        
        print(f"   ✓ 合并完成，共 {len(merged_df)} 行数据")
        
        # 计算全屋总负载
        merged_df['Site_Load'] = merged_df['Total_Load_F1'] + merged_df['Total_Load_F2']
        
        print(f"   ✓ 已计算 Site_Load，范围: {merged_df['Site_Load'].min():.2f} - {merged_df['Site_Load'].max():.2f} kW")
        
        return merged_df
    
    def resample_to_hourly(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        将分钟级数据重采样为小时级数据
        
        Args:
            df: 输入 DataFrame
            
        Returns:
            重采样后的 DataFrame
        """
        print("⏰ 正在重采样为小时级数据...")
        
        # 设置 Date 为索引
        df = df.set_index('Date')
        
        # 按小时重采样，对所有数值列求平均值
        hourly_df = df.resample('1H').mean()
        
        # 前向填充 NaN 值
        hourly_df = hourly_df.ffill()
        
        # 重置索引
        hourly_df = hourly_df.reset_index()
        
        print(f"   ✓ 重采样完成，从 {len(df)} 行压缩到 {len(hourly_df)} 行")
        print(f"   ✓ 已使用前向填充处理 NaN 值")
        
        return hourly_df
    
    def add_price_feature(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加电价特征（模拟峰谷电价）
        
        Args:
            df: 输入 DataFrame
            
        Returns:
            添加了电价列的 DataFrame
        """
        print("💰 正在添加电价特征...")
        
        def get_price(hour: int) -> float:
            """根据小时返回电价 (从配置读取)"""
            schedule = Config.PRICE_SCHEDULE
            
            if hour in schedule['peak_hours_list']:
                return schedule['peak']
            elif hour in schedule['normal_hours_list']:
                return schedule['normal']
            else:
                return schedule['valley']
        
        # 提取小时并映射电价
        df['Hour'] = df['Date'].dt.hour
        df['Price'] = df['Hour'].apply(get_price)
        
        schedule = Config.PRICE_SCHEDULE
        print(f"   ✓ 已添加 Price 列")
        print(f"   - 谷时 ({schedule['valley_desc']}): {schedule['valley']} {schedule['currency']}")
        print(f"   - 平时 ({schedule['normal_desc']}): {schedule['normal']} {schedule['currency']}")
        print(f"   - 峰时 ({schedule['peak_desc']}): {schedule['peak']} {schedule['currency']}")
        
        return df
    
    def add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加时间特征（基础版）
        
        Args:
            df: 输入 DataFrame
            
        Returns:
            添加了时间特征的 DataFrame
        """
        print("📅 正在添加时间特征...")
        
        # Hour 已在 add_price_feature 中添加
        if 'Hour' not in df.columns:
            df['Hour'] = df['Date'].dt.hour
        
        # 添加星期几 (0=Monday, 6=Sunday)
        df['DayOfWeek'] = df['Date'].dt.dayofweek
        
        print(f"   ✓ 已添加 Hour (0-23) 和 DayOfWeek (0-6) 特征")
        
        return df
    
    def add_enhanced_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加增强时间特征（月份、季节、节假日等）
        
        新增特征:
        - Month: 月份 (1-12)
        - Season: 季节 (0=春, 1=夏, 2=秋, 3=冬)
        - IsWeekend: 是否周末 (0/1)
        - IsHoliday: 是否节假日 (0/1)
        - DayOfMonth: 日期 (1-31)
        - WeekOfYear: 年内周数 (1-52)
        
        Args:
            df: 输入 DataFrame
            
        Returns:
            添加了增强时间特征的 DataFrame
        """
        print("📅 正在添加增强时间特征...")
        
        # 1. 月份 (1-12)
        df['Month'] = df['Date'].dt.month
        
        # 2. 季节 (基于北半球)
        # 春季: 3-5月, 夏季: 6-8月, 秋季: 9-11月, 冬季: 12-2月
        def get_season(month: int) -> int:
            if month in [3, 4, 5]:
                return 0  # 春
            elif month in [6, 7, 8]:
                return 1  # 夏
            elif month in [9, 10, 11]:
                return 2  # 秋
            else:
                return 3  # 冬
        
        df['Season'] = df['Month'].apply(get_season)
        
        # 3. 是否周末
        df['IsWeekend'] = (df['DayOfWeek'] >= 5).astype(int)
        
        # 4. 是否节假日（美国加州）
        if HOLIDAYS_AVAILABLE:
            # 使用 holidays 库判断美国加州节假日
            def is_us_holiday(date):
                try:
                    return int(date.date() in US_CA_HOLIDAYS)
                except:
                    return 0
            df['IsHoliday'] = df['Date'].apply(is_us_holiday)
            print("   ✓ 使用 holidays 库判断美国加州节假日 (CAISO 区域)")
        else:
            # 简化版：周末视为假日
            df['IsHoliday'] = df['IsWeekend']
            print("   ⚠️ 使用简化节假日判断（周末=假日）")
        
        # 5. 日期 (1-31)
        df['DayOfMonth'] = df['Date'].dt.day
        
        # 6. 年内周数 (1-52)
        df['WeekOfYear'] = df['Date'].dt.isocalendar().week.astype(int)
        
        print(f"   ✓ 已添加 Month (1-12)")
        print(f"   ✓ 已添加 Season (0=春, 1=夏, 2=秋, 3=冬)")
        print(f"   ✓ 已添加 IsWeekend (0/1)")
        print(f"   ✓ 已添加 IsHoliday (0/1)")
        print(f"   ✓ 已添加 DayOfMonth (1-31)")
        print(f"   ✓ 已添加 WeekOfYear (1-52)")
        
        return df

    def add_advanced_features(self, df: pd.DataFrame, dropna: bool = True, use_enhanced: bool = True) -> pd.DataFrame:
        """
        添加高级特征 (Lag, Rolling, Interaction)
        实现论文第3章描述的特征工程
        
        Args:
            df: 输入 DataFrame
            dropna: 是否删除因特征构建产生的 NaN 行 (默认 True)
            use_enhanced: 是否使用增强特征（需要先调用 add_enhanced_time_features）
        """
        print("🚀 正在添加高级特征 (Lag, Rolling, Interaction)...")
        
        # 确保数据按时间排序
        df = df.sort_values('Date').reset_index(drop=True)
        
        # 1. 滞后特征 (Lag Features)
        # Lag 1h: 上一小时负载
        df['Lag_1h'] = df['Site_Load'].shift(1)
        # Lag 24h: 昨日此时
        df['Lag_24h'] = df['Site_Load'].shift(24)
        # Lag 168h: 上周此时
        df['Lag_168h'] = df['Site_Load'].shift(168)
        
        # 2. 滑动窗口特征 (Rolling Window Statistics)
        # 必须先 shift(1) 避免未来信息泄露 (Data Leakage)
        # 使用 shift(1) 后，rolling 取的是 t-1, t-2... 的数据
        
        # 过去6小时均值
        df['Rolling_Mean_6h'] = df['Site_Load'].shift(1).rolling(window=6).mean()
        # 过去6小时标准差
        df['Rolling_Std_6h'] = df['Site_Load'].shift(1).rolling(window=6).std()
        # 过去24小时均值
        df['Rolling_Mean_24h'] = df['Site_Load'].shift(1).rolling(window=24).mean()
        
        # 3. 基础交互特征 (Interaction Features)
        # Temperature x Hour: 捕捉不同时段温度的影响差异 (如中午高温vs深夜高温)
        df['Temp_x_Hour'] = df['Temperature'] * df['Hour']
        
        # Lag_24h x DayOfWeek: 捕捉历史负载在不同星期的惯性差异
        df['Lag24_x_DayOfWeek'] = df['Lag_24h'] * df['DayOfWeek']
        
        # 4. 增强交互特征（如果有增强时间特征）
        enhanced_features_added = []
        if use_enhanced and 'Season' in df.columns:
            # Temperature x Season: 捕捉不同季节的温度效应差异
            df['Temp_x_Season'] = df['Temperature'] * df['Season']
            enhanced_features_added.append('Temp*Season')
            
            # Load_Lag24 x IsWeekend: 周末与工作日的历史惯性差异
            if 'IsWeekend' in df.columns:
                df['Lag24_x_IsWeekend'] = df['Lag_24h'] * df['IsWeekend']
                enhanced_features_added.append('Lag24*IsWeekend')
            
            # Hour x IsHoliday: 节假日不同时段的用电模式
            if 'IsHoliday' in df.columns:
                df['Hour_x_IsHoliday'] = df['Hour'] * df['IsHoliday']
                enhanced_features_added.append('Hour*IsHoliday')
            
            # 季节性周期编码 (正弦/余弦变换捕捉周期性)
            # 月份周期 (12个月)
            df['Month_Sin'] = np.sin(2 * np.pi * df['Month'] / 12)
            df['Month_Cos'] = np.cos(2 * np.pi * df['Month'] / 12)
            enhanced_features_added.extend(['Month_Sin', 'Month_Cos'])
            
            # 小时周期 (24小时)
            df['Hour_Sin'] = np.sin(2 * np.pi * df['Hour'] / 24)
            df['Hour_Cos'] = np.cos(2 * np.pi * df['Hour'] / 24)
            enhanced_features_added.extend(['Hour_Sin', 'Hour_Cos'])
        
        # 5. 清洗 NaN (由于 shift/rolling 产生的头部缺失)
        original_len = len(df)
        
        if dropna:
            df = df.dropna().reset_index(drop=True)
            dropped_len = original_len - len(df)
            print(f"   ✓ 已添加 Lag: 1h, 24h, 168h")
            print(f"   ✓ 已添加 Rolling: Mean(6h, 24h), Std(6h)")
            print(f"   ✓ 已添加 Interaction: Temp*Hour, Lag24*DoW")
            if enhanced_features_added:
                print(f"   ✓ 已添加增强交互特征: {', '.join(enhanced_features_added)}")
            print(f"   ⚠️  因特征构建剔除了前 {dropped_len} 行数据 (Warm-up Period)")
        else:
            print(f"   ✓ 已添加高级特征 (保留 NaN 行，共 {original_len} 行)")
        
        return df
    
    def save_processed_data(self, df: pd.DataFrame, filename: str = 'cleaned_energy_data.csv') -> Path:
        """
        保存处理后的数据
        
        Args:
            df: 处理后的 DataFrame
            filename: 输出文件名
            
        Returns:
            输出文件路径
        """
        output_path = self.output_dir / filename
        
        print(f"💾 正在保存处理后的数据到: {output_path}")
        df.to_csv(output_path, index=False)
        print(f"   ✓ 保存成功！")
        
        return output_path
    
    def print_summary(self, df: pd.DataFrame):
        """
        打印数据摘要
        
        Args:
            df: DataFrame
        """
        print("\n" + "="*80)
        print("📊 数据处理完成！以下是处理后的数据摘要：")
        print("="*80)
        
        print(f"\n📈 数据形状: {df.shape[0]} 行 × {df.shape[1]} 列")
        
        print(f"\n📋 前 5 行数据:")
        print(df.head().to_string())
        
        print(f"\n📊 数据统计信息:")
        print(df.describe().to_string())
        
        print(f"\n🔍 列名列表:")
        for i, col in enumerate(df.columns, 1):
            print(f"   {i}. {col}")
        
        print(f"\n✅ 总行数: {len(df)}")
        print("="*80 + "\n")


def preprocess_energy_data(
    raw_data_dir: str = None,
    output_dir: str = None,
    year: str = None,
    floors: List[int] = None,
    output_file: str = None
) -> pd.DataFrame:
    """
    完整的能源数据预处理流程 - 支持多楼层多年份数据
    
    Args:
        raw_data_dir: 原始数据目录路径（默认为 data/raw）
        output_dir: 输出数据目录路径（默认为 data/processed）
        year: 年份（'2018', '2019', 或 None 表示所有年份）
        floors: 楼层列表（例如 [1, 2, 3] 或 None 表示所有楼层）
        output_file: 输出文件名（默认根据年份自动生成）
        
    Returns:
        处理后的 DataFrame
    """
    print("\n" + "🚀 " + "="*76)
    print("🏠 家庭微网能源优化系统 - 数据预处理流程（多楼层版本）")
    print("="*78 + "\n")
    
    # 初始化处理器
    processor = EnergyDataProcessor(raw_data_dir, output_dir)
    
    # 自动发现所有数据文件
    import glob
    import os
    
    pattern = os.path.join(processor.raw_data_dir, '*.csv')
    all_files = sorted(glob.glob(pattern))
    all_files = [f for f in all_files if not f.endswith('.gitkeep')]
    
    print(f"📂 发现 {len(all_files)} 个数据文件")
    
    # 过滤文件
    selected_files = []
    for file_path in all_files:
        filename = os.path.basename(file_path)
        if not filename.endswith('.csv'):
            continue
        
        # 提取年份和楼层
        try:
            file_year = filename[:4]
            floor_num = int(filename.replace(file_year, '').replace('Floor', '').replace('.csv', ''))
            
            # 应用过滤条件
            if year and file_year != year:
                continue
            if floors and floor_num not in floors:
                continue
            
            selected_files.append((file_path, file_year, floor_num))
        except:
            continue
    
    if not selected_files:
        raise ValueError("未找到符合条件的数据文件")
    
    print(f"✅ 选择了 {len(selected_files)} 个文件进行处理:")
    for file_path, file_year, floor_num in selected_files:
        print(f"   - {file_year}Floor{floor_num}.csv")
    
    # Step 1: 读取所有数据
    print("\n【步骤 1/6】读取原始数据")
    print("-" * 80)
    
    all_floors_data = []
    temperature_data = None
    
    for file_path, file_year, floor_num in selected_files:
        try:
            df = processor.read_csv_with_date(Path(file_path))
            
            # 确保 Date 列是 datetime 类型，使用 errors='coerce' 处理异常值
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            
            # 删除 Date 为 NaT 的行
            invalid_dates = df['Date'].isna().sum()
            if invalid_dates > 0:
                print(f"   ⚠️  发现 {invalid_dates} 行无效日期，已删除")
                df = df.dropna(subset=['Date'])
            
            # Step 2: 特征聚合
            df = processor.aggregate_power_columns(df, f'{file_year}_F{floor_num}')
            
            # 提取温度数据（如果有）
            temp_columns = [col for col in df.columns if 'degC' in col]
            if temp_columns and temperature_data is None:
                df_temp = processor.extract_temperature(df.copy())
                temperature_data = df_temp[['Date', 'Temperature']].copy()
            
            # 保留Date和总负载列
            load_col = f'Total_Load_{file_year}_F{floor_num}'
            all_floors_data.append(df[['Date', load_col]].copy())
            
        except Exception as e:
            print(f"   ❌ 处理 {file_year}Floor{floor_num}.csv 时出错: {str(e)}")
            print(f"   跳过此文件，继续处理其他文件...")
    
    print("\n【步骤 2/6】特征聚合")
    print("-" * 80)
    print(f"✓ 已聚合 {len(all_floors_data)} 个楼层的功率数据")
    
    # Step 3: 数据合并
    print("\n【步骤 3/6】数据合并")
    print("-" * 80)
    
    # 合并所有楼层数据
    # 使用 outer join 以保留所有时间点，缺失值用 0 填充
    merged_df = all_floors_data[0]
    for df in all_floors_data[1:]:
        merged_df = pd.merge(merged_df, df, on='Date', how='outer')
    
    # 对负载列的缺失值填充为 0（该时间点该楼层无数据）
    load_columns = [col for col in merged_df.columns if col.startswith('Total_Load_')]
    merged_df[load_columns] = merged_df[load_columns].fillna(0)
    
    # 合并温度数据
    if temperature_data is not None:
        merged_df = pd.merge(merged_df, temperature_data, on='Date', how='left')
        # 温度缺失值用前后值插值填充
        merged_df['Temperature'] = merged_df['Temperature'].interpolate(method='linear').fillna(25.0)
    
    # 计算全站总负载
    load_columns = [col for col in merged_df.columns if col.startswith('Total_Load_')]
    merged_df['Site_Load'] = merged_df[load_columns].sum(axis=1)
    
    print(f"   ✓ 合并完成，共 {len(merged_df)} 行数据")
    print(f"   ✓ 已计算 Site_Load，范围: {merged_df['Site_Load'].min():.2f} - {merged_df['Site_Load'].max():.2f} kW")
    
    # Step 4: 重采样
    print("\n【步骤 4/6】重采样为小时级数据")
    print("-" * 80)
    hourly_df = processor.resample_to_hourly(merged_df)
    
    # Step 5: 特征工程
    print("\n【步骤 5/6】特征工程")
    print("-" * 80)
    hourly_df = processor.add_price_feature(hourly_df)
    hourly_df = processor.add_time_features(hourly_df)
    hourly_df = processor.add_advanced_features(hourly_df)
    
    # Step 6: 保存数据
    print("\n【步骤 6/6】保存处理后的数据")
    print("-" * 80)
    
    # 自动生成输出文件名
    if output_file is None:
        if year:
            output_file = f'cleaned_energy_data_{year}.csv'
        else:
            output_file = 'cleaned_energy_data_all.csv'
    
    processor.save_processed_data(hourly_df, output_file)
    
    # 打印摘要
    processor.print_summary(hourly_df)
    
    return hourly_df


def preprocess_all_data(raw_data_dir: str = None, output_dir: str = None):
    """
    处理所有年份和楼层的数据
    
    Args:
        raw_data_dir: 原始数据目录
        output_dir: 输出目录
    """
    print("\n" + "="*80)
    print("🌟 开始处理所有数据文件...")
    print("="*80 + "\n")
    
    # 处理 2018 年所有楼层
    print("\n" + "#"*80)
    print("# 处理 2018 年数据")
    print("#"*80)
    df_2018 = preprocess_energy_data(
        raw_data_dir=raw_data_dir,
        output_dir=output_dir,
        year='2018',
        output_file='cleaned_energy_data_2018.csv'
    )
    
    # 处理 2019 年所有楼层
    print("\n" + "#"*80)
    print("# 处理 2019 年数据")
    print("#"*80)
    df_2019 = preprocess_energy_data(
        raw_data_dir=raw_data_dir,
        output_dir=output_dir,
        year='2019',
        output_file='cleaned_energy_data_2019.csv'
    )
    
    # 合并所有年份数据（使用 concat 而不是 merge）
    print("\n" + "#"*80)
    print("# 合并所有年份数据")
    print("#"*80)
    print("正在合并 2018 和 2019 年数据...")
    
    # 确保两个DataFrame有相同的列
    common_cols = [
        'Date', 'Site_Load', 'Temperature', 'Hour', 'Price', 'DayOfWeek',
        'Lag_1h', 'Lag_24h', 'Lag_168h',
        'Rolling_Mean_6h', 'Rolling_Std_6h', 'Rolling_Mean_24h',
        'Temp_x_Hour', 'Lag24_x_DayOfWeek'
    ]
    df_2018_subset = df_2018[common_cols].copy()
    df_2019_subset = df_2019[common_cols].copy()
    
    # 使用 concat 合并
    df_all = pd.concat([df_2018_subset, df_2019_subset], ignore_index=True)
    df_all = df_all.sort_values('Date').reset_index(drop=True)
    
    # 保存合并后的数据
    processor = EnergyDataProcessor(raw_data_dir, output_dir)
    processor.save_processed_data(df_all, 'cleaned_energy_data_all.csv')
    
    print(f"✓ 合并完成，总共 {len(df_all)} 行数据")
    print(f"  - 日期范围: {df_all['Date'].min()} 到 {df_all['Date'].max()}")
    
    print("\n" + "="*80)
    print("🎉 所有数据处理完成！")
    print("="*80)
    print(f"\n📊 处理结果汇总:")
    print(f"   - 2018年数据: {len(df_2018)} 行")
    print(f"   - 2019年数据: {len(df_2019)} 行")
    print(f"   - 全部数据: {len(df_all)} 行")
    print(f"\n📁 输出文件:")
    print(f"   - cleaned_energy_data_2018.csv")
    print(f"   - cleaned_energy_data_2019.csv")
    print(f"   - cleaned_energy_data_all.csv")
    print("\n")
    
    return df_2018, df_2019, df_all


if __name__ == '__main__':
    """
    主函数 - 执行完整的数据预处理流程
    """
    # 处理所有数据
    preprocess_all_data()
    
    print("🎉 数据预处理流程全部完成！")
    print(f"📁 处理后的数据已保存，可用于模型训练。\n")
