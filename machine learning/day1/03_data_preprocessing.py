"""
数据预处理入门示例
展示数据清洗、标准化、特征缩放等基础操作
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.impute import SimpleImputer

print("=" * 50)
print("数据预处理示例")
print("=" * 50)

# 1. 创建含有缺失值和异常值的数据集
data = {
    '年龄': [25, 30, np.nan, 45, 50, 28, np.nan, 35],
    '收入': [3000, 5000, 4000, np.nan, 8000, 4500, 3500, 6000],
    '学分': [3.5, 3.8, 3.2, 3.9, 3.1, 3.6, 3.4, 3.7]
}

df = pd.DataFrame(data)

print("\n1. 原始数据:")
print(df)
print(f"\n缺失值统计:\n{df.isnull().sum()}")

# 2. 处理缺失值
print("\n2. 处理缺失值:")

# 方法1: 用平均值填充
imputer = SimpleImputer(strategy='mean')
df_filled = df.copy()
df_filled[['年龄', '收入']] = imputer.fit_transform(df[['年龄', '收入']])

print("用平均值填充后的数据:")
print(df_filled)

# 3. 特征缩放 - 标准化（Standardization）
print("\n3. 标准化（Z-score）:")

scaler_standard = StandardScaler()
X_standard = scaler_standard.fit_transform(df_filled[['年龄', '收入']])

df_standard = pd.DataFrame(
    X_standard, 
    columns=['年龄_标准化', '收入_标准化']
)
print(df_standard)
print(f"\n标准化后统计:")
print(f"  均值: {X_standard.mean(axis=0)}")
print(f"  标准差: {X_standard.std(axis=0)}")

# 4. 特征缩放 - 归一化（Normalization）
print("\n4. 归一化（Min-Max）:")

scaler_minmax = MinMaxScaler(feature_range=(0, 1))
X_minmax = scaler_minmax.fit_transform(df_filled[['年龄', '收入']])

df_minmax = pd.DataFrame(
    X_minmax, 
    columns=['年龄_归一化', '收入_归一化']
)
print(df_minmax)
print(f"\n归一化后统计:")
print(f"  最小值: {X_minmax.min(axis=0)}")
print(f"  最大值: {X_minmax.max(axis=0)}")

# 5. 数据统计和探索
print("\n5. 数据统计摘要:")
print(df_filled.describe())

# 6. 数据质量检查
print("\n6. 数据质量检查:")
print(f"  重复行数: {df_filled.duplicated().sum()}")
print(f"  完整行数: {df_filled.shape[0] - df_filled.isnull().sum().sum()}/{df_filled.shape[0]}")

# 7. 特征关系分析
print("\n7. 特征相关性:")
correlation = df_filled.corr()
print(correlation)

# 8. 离群值检测（使用IQR方法）
print("\n8. 离群值检测（IQR方法）:")

for column in df_filled.columns:
    Q1 = df_filled[column].quantile(0.25)
    Q3 = df_filled[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    outliers = df_filled[(df_filled[column] < lower_bound) | 
                         (df_filled[column] > upper_bound)]
    
    print(f"\n  {column}:")
    print(f"    范围: [{lower_bound:.2f}, {upper_bound:.2f}]")
    print(f"    离群值数量: {len(outliers)}")
    if len(outliers) > 0:
        print(f"    离群值: {outliers[column].values}")

print("\n预处理完成！")
