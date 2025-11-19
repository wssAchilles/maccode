# 快速参考卡 - 增强数据分析功能

## 🚀 快速开始

### 安装依赖

```bash
cd /Users/achilles/Documents/code/data\ science
source venv/bin/activate
pip install scipy==1.11.4
```

### 运行测试

```bash
python back/services/test_analysis_enhanced.py
```

---

## 📦 三个核心方法

### 1️⃣ 质量检查 (Week 03 & 13)

```python
from back.services.analysis_service import AnalysisService
import pandas as pd

df = pd.read_csv('data.csv')
result = AnalysisService.perform_quality_check(df)

# 输出
result['quality_score']           # 0-100 分
result['high_risk_columns']       # 缺失率>5%的列
result['outlier_detection']       # 异常值详情
result['recommendations']         # 改进建议
```

**返回的关键字段**:

- `quality_score`: 质量分数
- `missing_analysis`: 缺失值详情
- `outlier_detection`: 异常值（IQR方法）
- `duplicate_check`: 重复行统计
- `data_summary`: 按类型的数据摘要

---

### 2️⃣ 相关性分析 (Week 05)

```python
result = AnalysisService.calculate_correlations(df)

# 输出
result['correlations']            # 所有变量对的相关性
result['high_correlations']       # |r|>0.7 的变量对
result['pearson_matrix']          # Pearson 矩阵
result['spearman_matrix']         # Spearman 矩阵
result['suggestions']             # 多重共线性建议
```

**返回的关键字段**:

- `correlations`: 详细相关性列表（含 p-value）
- `high_correlations`: 高相关变量对
- `pearson_matrix`: 完整 Pearson 矩阵
- `spearman_matrix`: 完整 Spearman 矩阵

---

### 3️⃣ 统计检验 (Week 04)

```python
result = AnalysisService.perform_statistical_tests(df)

# 输出
result['normality_tests']         # 每列的正态性检验
result['non_normal_columns']      # 非正态分布列
result['summary']                 # 汇总统计
result['suggestions']             # 转换建议
```

**返回的关键字段**:

- `normality_tests`: 每列的 Shapiro-Wilk 或 D'Agostino-Pearson 检验
- `non_normal_columns`: 非正态列名列表
- `suggestions`: 数据转换和方法选择建议

---

## 🔥 一键综合分析

```python
# 推荐：一次性执行所有分析
quality = AnalysisService.perform_quality_check(df)
corr = AnalysisService.calculate_correlations(df)
stats = AnalysisService.perform_statistical_tests(df)

print(f"质量: {quality['quality_score']}/100")
print(f"高相关: {len(corr['high_correlations'])} 对")
print(f"非正态: {len(stats['non_normal_columns'])} 列")
```

---

## 🎯 实际应用场景

### 场景1: 数据接收质量检查

```python
# 新数据到达，立即检查质量
quality = AnalysisService.perform_quality_check(df)

if quality['quality_score'] < 70:
    print("❌ 数据质量不合格")
    print(quality['recommendations'])
    # 拒绝数据或触发清洗流程
else:
    print("✅ 数据质量合格，继续处理")
```

### 场景2: 建模前预检查

```python
# 建模前检查多重共线性
corr = AnalysisService.calculate_correlations(df)

if corr['high_correlations']:
    print("⚠️ 警告：发现多重共线性")
    for hc in corr['high_correlations']:
        print(f"  {hc['variables'][0]} ↔️ {hc['variables'][1]}: r={hc['correlation']}")
```

### 场景3: 选择合适的统计方法

```python
# 确定是否使用参数检验
stats = AnalysisService.perform_statistical_tests(df)

if stats['non_normal_columns']:
    print("📊 建议使用非参数方法")
    print(f"非正态列: {stats['non_normal_columns']}")
else:
    print("📊 可以使用参数方法 (t-test, Pearson)")
```

---

## 📊 返回结果速查

### Quality Check 关键指标

```json
{
  "quality_score": 85.5,           // 0-100
  "high_risk_columns": ["col1"],   // 缺失率>5%
  "quality_metrics": {
    "total_missing": 50,           // 总缺失数
    "missing_rate": 5.0,           // 缺失率%
    "total_outliers": 15,          // 异常值数
    "duplicate_rows": 3            // 重复行数
  }
}
```

### Correlation 关键指标

```json
{
  "correlations": [
    {
      "variable_x": "age",
      "variable_y": "income",
      "pearson": {
        "correlation": 0.7523,
        "p_value": 0.000012,
        "significant": true          // p<0.05
      }
    }
  ],
  "high_correlations": [...]         // |r|>0.7
}
```

### Statistical Test 关键指标

```json
{
  "normality_tests": {
    "age": {
      "test_name": "Shapiro-Wilk",
      "p_value": 0.234567,
      "is_normal": true,             // p>=0.05
      "skewness": 0.15,
      "kurtosis": -0.5
    }
  },
  "non_normal_columns": ["income"]
}
```

---

## ⚡ 性能提示

| 数据规模 | 建议 |
|---------|-----|
| < 1,000 行 | 直接使用所有方法 |
| 1,000 - 10,000 | 正常使用 |
| 10,000 - 100,000 | 考虑采样或分批 |
| > 100,000 | 使用采样（不影响 IQR 和相关性计算） |

---

## 🔍 判断标准速查

### 质量分数判断

- **90-100**: 优秀 ✅
- **70-89**: 良好 ⚠️
- **50-69**: 需要清洗 ⚠️⚠️
- **< 50**: 不合格 ❌

### 相关性强度

- **|r| > 0.7**: 强相关 ⚠️ 注意多重共线性
- **0.4 < |r| < 0.7**: 中等相关
- **|r| < 0.4**: 弱相关 ✅

### 缺失值风险

- **> 5%**: 高风险 ❌ 需要处理
- **1-5%**: 中等风险 ⚠️
- **< 1%**: 低风险 ✅

---

## 🚨 常见错误处理

### 错误1: 样本量不足

```python
# 检查样本量
if len(df) < 3:
    print("❌ 样本量不足，至少需要3个观测值")
```

### 错误2: 无数值列

```python
result = AnalysisService.calculate_correlations(df)
if not result['success']:
    print(f"❌ {result['message']}")
    # "需要至少2个数值列才能计算相关性"
```

### 错误3: 全是NaN

```python
# 方法内部已处理，会跳过全NaN列
# 检查警告信息
if 'error' in result['outlier_detection']['col_name']:
    print(f"⚠️ 列处理警告: {result['outlier_detection']['col_name']['error']}")
```

---

## 📚 完整文档链接

- 详细功能说明: `docs/ENHANCED_ANALYSIS_GUIDE.md`
- API 集成示例: `docs/API_INTEGRATION_EXAMPLE.md`
- 实现总结: `IMPLEMENTATION_SUMMARY.md`
- 测试代码: `back/services/test_analysis_enhanced.py`

---

## 💡 最佳实践

1. ✅ **先质量检查，再分析**: 确保数据质量合格
2. ✅ **检查分布，选方法**: 根据正态性选择参数/非参数方法
3. ✅ **注意多重共线性**: 建模前检查高相关变量
4. ✅ **阅读建议**: 每个方法都返回 `suggestions` 字段
5. ✅ **错误处理**: 始终检查 `result['success']`

---

## 🎓 课程对应关系

| 方法 | 课程 | 核心概念 |
|-----|-----|---------|
| `perform_quality_check` | Week 03, 13 | Garbage in, garbage out |
| `calculate_correlations` | Week 05 | Correlation reveals association |
| `perform_statistical_tests` | Week 04 | Implementation Tips |

---

## ✨ 记住这些

```python
# 三个方法，一个目标：让数据分析更科学
quality = AnalysisService.perform_quality_check(df)      # 质量评估
corr = AnalysisService.calculate_correlations(df)        # 关系分析
stats = AnalysisService.perform_statistical_tests(df)    # 分布检验

# 三个问题，一个流程：
# 1. 数据质量如何？ → quality_score
# 2. 变量相关吗？   → high_correlations
# 3. 分布正态吗？   → non_normal_columns
```

---

**版本**: v1.0.0  
**状态**: ✅ 生产就绪  
**测试**: ✅ 已通过
