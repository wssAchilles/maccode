# 增强数据分析功能指南

## 概述

本文档介绍了根据课程 Week 03, 04, 05, 13 内容增强的数据分析功能。

## Phase 1: 数据质量评估 (Week 03 & Week 13)

### 功能：`perform_quality_check(df)`

生成详细的数据质量报告，实现"Garbage in, garbage out"的质量保证。

#### 核心功能

1. **缺失值分析**
   - 计算每列的缺失数量和比例
   - 自动标记缺失率 >5% 的"高风险列"
   - 判断缺失机制

2. **异常值检测**
   - 使用 IQR (Interquartile Range) 方法
   - 异常值定义：< Q1 - 1.5×IQR 或 > Q3 + 1.5×IQR
   - 返回异常值的行索引和比例

3. **重复数据检查**
   - 统计完全重复的行
   - 返回重复行的索引

4. **数据摘要**
   - **数值列**: Mean, Median, Std, Skewness, Kurtosis, Min, Max
   - **类别列**: Unique count, Top values
   - **时间列**: Min, Max, Range

5. **质量分数**
   - 0-100 分制
   - 基于缺失率、异常值比例和重复率计算

#### 使用示例

```python
from back.services.analysis_service import AnalysisService
import pandas as pd

# 读取数据
df = pd.read_csv('your_data.csv')

# 执行质量检查
result = AnalysisService.perform_quality_check(df)

if result['success']:
    print(f"质量分数: {result['quality_score']}/100")
    print(f"高风险列: {result['high_risk_columns']}")
    print(f"异常值统计: {result['outlier_detection']}")
    print(f"建议: {result['recommendations']}")
```

#### 返回结果结构

```json
{
  "success": true,
  "quality_score": 85.5,
  "missing_analysis": {
    "column_name": {
      "count": 10,
      "percentage": 10.5,
      "risk_level": "High Missing Risk"
    }
  },
  "high_risk_columns": ["column_name"],
  "outlier_detection": {
    "numeric_column": {
      "count": 5,
      "percentage": 5.0,
      "indices": [1, 5, 10, 25, 50],
      "bounds": {
        "lower": -10.5,
        "upper": 110.5
      }
    }
  },
  "duplicate_check": {
    "count": 3,
    "percentage": 3.0,
    "indices": [10, 20, 30]
  },
  "data_summary": {
    "numeric_columns": {
      "age": {
        "mean": 35.5,
        "median": 34.0,
        "std": 12.3,
        "skewness": 0.15,
        "kurtosis": -0.8,
        "min": 18.0,
        "max": 85.0
      }
    },
    "categorical_columns": {
      "category": {
        "unique_count": 5,
        "top_values": {"A": 30, "B": 25, "C": 20},
        "most_common": "A"
      }
    }
  },
  "quality_metrics": {
    "total_cells": 1000,
    "total_missing": 50,
    "missing_rate": 5.0,
    "total_outliers": 15,
    "duplicate_rows": 3
  },
  "recommendations": [
    "警告：发现 1 个高缺失风险列 (income)。建议考虑删除这些列或使用插补方法处理缺失值。"
  ]
}
```

---

## Phase 2: 统计分析与相关性 (Week 04 & Week 05)

### 功能：`calculate_correlations(df)`

计算变量间的相关性，实现"Correlation reveals association"。

#### 核心功能

1. **Pearson 相关系数**
   - 衡量线性相关性
   - 包含 p-value 和显著性判断

2. **Spearman 相关系数**
   - 衡量单调相关性
   - 适用于非线性关系

3. **高相关性检测**
   - 自动标记 |r| > 0.7 的变量对
   - 生成多重共线性警告

4. **相关性矩阵**
   - Pearson 和 Spearman 完整矩阵
   - 便于前端绘制热力图

#### 使用示例

```python
# 计算相关性
result = AnalysisService.calculate_correlations(df)

if result['success']:
    print(f"相关性对数: {len(result['correlations'])}")
    print(f"高相关变量: {result['high_correlations']}")
    print(f"建议: {result['suggestions']}")
    
    # 获取矩阵用于可视化
    pearson_matrix = result['pearson_matrix']
    spearman_matrix = result['spearman_matrix']
```

#### 返回结果结构

```json
{
  "success": true,
  "correlations": [
    {
      "variable_x": "age",
      "variable_y": "income",
      "pearson": {
        "correlation": 0.7523,
        "p_value": 0.000012,
        "significant": true
      },
      "spearman": {
        "correlation": 0.7102,
        "p_value": 0.000045,
        "significant": true
      },
      "n_samples": 95
    }
  ],
  "high_correlations": [
    {
      "variables": ["age", "income"],
      "correlation": 0.7523,
      "type": "positive"
    }
  ],
  "pearson_matrix": {
    "age": {"age": 1.0, "income": 0.7523},
    "income": {"age": 0.7523, "income": 1.0}
  },
  "spearman_matrix": {...},
  "suggestions": [
    "发现变量 'age' 与 'income' 存在强positive相关性 (r=0.752)。建议在回归模型中注意多重共线性问题，考虑使用VIF检验或移除其中一个变量。"
  ],
  "numeric_columns": ["age", "income", "score"]
}
```

---

### 功能：`perform_statistical_tests(df)`

执行分布检验，实现 Week 04 的"Implementation Tips"。

#### 核心功能

1. **正态性检验**
   - **Shapiro-Wilk** (n < 5000): 适合小样本
   - **D'Agostino-Pearson** (n ≥ 5000): 适合大样本
   - p-value < 0.05 标记为"非正态分布"

2. **分布特征**
   - Skewness (偏度)
   - Kurtosis (峰度)

3. **自动建议**
   - 非正态分布的处理方法
   - 数据转换建议（对数、Box-Cox）
   - 非参数检验方法推荐

#### 使用示例

```python
# 执行统计检验
result = AnalysisService.perform_statistical_tests(df)

if result['success']:
    print(f"检验列数: {result['summary']['total_numeric_columns']}")
    print(f"正态分布: {result['summary']['normal_distribution_count']}")
    print(f"非正态分布: {result['summary']['non_normal_distribution_count']}")
    print(f"非正态列: {result['non_normal_columns']}")
    print(f"建议: {result['suggestions']}")
```

#### 返回结果结构

```json
{
  "success": true,
  "normality_tests": {
    "age": {
      "test_name": "Shapiro-Wilk",
      "statistic": 0.9876,
      "p_value": 0.234567,
      "is_normal": true,
      "distribution": "正态分布",
      "n_samples": 100,
      "skewness": 0.15,
      "kurtosis": -0.5
    },
    "income": {
      "test_name": "Shapiro-Wilk",
      "statistic": 0.8234,
      "p_value": 0.000123,
      "is_normal": false,
      "distribution": "非正态分布",
      "n_samples": 100,
      "skewness": 2.34,
      "kurtosis": 5.67
    }
  },
  "non_normal_columns": ["income"],
  "summary": {
    "total_numeric_columns": 3,
    "normal_distribution_count": 2,
    "non_normal_distribution_count": 1
  },
  "suggestions": [
    "发现 1 个非正态分布的数值列：income。",
    "列 'income' 偏度较高 (skewness=2.34)。建议考虑对数转换或Box-Cox转换来改善正态性。",
    "对于非正态分布的数据，建议：(1) 使用非参数检验方法（如Spearman相关、Mann-Whitney U检验）；(2) 考虑数据转换；(3) 使用稳健统计方法。"
  ]
}
```

---

## 完整工作流示例

```python
from back.services.analysis_service import AnalysisService
import pandas as pd

# 读取数据
df = pd.read_csv('your_data.csv')

# Step 1: 质量检查
print("=== Phase 1: 数据质量评估 ===")
quality_result = AnalysisService.perform_quality_check(df)

if quality_result['quality_score'] < 70:
    print("警告：数据质量分数较低，建议先进行数据清洗！")
    print(f"建议：{quality_result['recommendations']}")
else:
    print(f"✓ 数据质量良好 (分数: {quality_result['quality_score']}/100)")

# Step 2: 统计检验
print("\n=== Phase 2: 统计检验 ===")
stat_result = AnalysisService.perform_statistical_tests(df)

if stat_result['non_normal_columns']:
    print(f"注意：{len(stat_result['non_normal_columns'])} 列为非正态分布")
    print(f"建议：{stat_result['suggestions']}")

# Step 3: 相关性分析
print("\n=== Phase 2: 相关性分析 ===")
corr_result = AnalysisService.calculate_correlations(df)

if corr_result['high_correlations']:
    print(f"发现 {len(corr_result['high_correlations'])} 对高相关变量")
    print(f"建议：{corr_result['suggestions']}")
else:
    print("✓ 变量之间相对独立，无多重共线性问题")

print("\n=== 分析完成 ===")
```

---

## 课程对应关系

| 功能 | 对应课程 | 核心理念 |
|------|---------|---------|
| 缺失值分析 | Week 03 | Garbage in, garbage out |
| 异常值检测 | Week 03 | Mathematical Essence (IQR) |
| 数据质量评估 | Week 13 | Data quality assessment |
| 正态性检验 | Week 04 | Implementation Tips |
| 相关性分析 | Week 05 | Correlation reveals association |

---

## 依赖库

```txt
pandas==2.1.3
numpy==1.26.2
scipy==1.11.4  # 新增，用于统计检验
```

---

## 错误处理

所有方法都包含完善的错误处理机制：

```python
result = AnalysisService.perform_quality_check(df)

if result['success']:
    # 处理成功结果
    quality_score = result['quality_score']
else:
    # 处理错误
    error_message = result['message']
    error_code = result['error']
```

---

## 性能考虑

1. **样本量限制**：返回的异常值和重复行索引限制在前100个
2. **大数据集**：对于 n ≥ 5000 的数据，自动使用更快的 D'Agostino-Pearson 检验
3. **NaN 处理**：所有计算前自动移除 NaN 值，避免计算错误

---

## 后续扩展建议

1. **可视化支持**：添加热力图、分布图生成
2. **自动清洗**：基于质量报告自动执行数据清洗
3. **报告导出**：生成 PDF/HTML 格式的质量报告
4. **实时监控**：集成到数据管道中进行实时质量监控

---

## 联系与支持

如有问题，请参考：

- 课程内容：Week 03, 04, 05, 13
- 代码位置：`back/services/analysis_service.py`
- 测试文件：`back/services/test_analysis_enhanced.py`
