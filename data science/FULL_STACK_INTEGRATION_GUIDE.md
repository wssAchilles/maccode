# 全栈集成指南

## 📋 完成状态

✅ **后端 API 升级完成**  
✅ **Flutter 数据模型完成**  
✅ **可视化组件完成**  
✅ **响应式 UI 完成**

---

## 🚀 第一步：后端依赖安装

### 1. 激活虚拟环境并安装 scipy

```bash
cd "/Users/achilles/Documents/code/data science"
source venv/bin/activate
pip install scipy==1.11.4
```

### 2. 验证后端安装

```bash
# 运行测试
python back/services/test_analysis_enhanced.py

# 预期输出：
# ✓ 质量分数: 92.22/100
# ✓ 所有测试完成
```

### 3. 启动后端服务（本地测试）

```bash
# 确保在虚拟环境中
source venv/bin/activate

# 启动 Flask 开发服务器
python back/main.py

# 服务将运行在 http://localhost:8080
```

---

## 🎨 第二步：前端依赖安装

### 1. 进入前端目录

```bash
cd "/Users/achilles/Documents/code/data science/front"
```

### 2. 安装 Flutter 依赖

```bash
flutter pub get
```

这将安装以下新增的可视化库：

- `fl_chart: ^0.69.0` - 图表库
- `percent_indicator: ^4.2.3` - 进度指示器

### 3. 验证安装

```bash
flutter doctor

# 确保没有严重错误
```

---

## 📱 第三步：运行应用

### 方式 A：Web 开发模式（推荐）

```bash
cd "/Users/achilles/Documents/code/data science/front"

# 运行在 Chrome
flutter run -d chrome

# 或指定端口
flutter run -d chrome --web-port=3000
```

### 方式 B：桌面应用（macOS）

```bash
flutter run -d macos
```

### 方式 C：移动端

```bash
# iOS Simulator
flutter run -d "iPhone 15"

# Android Emulator
flutter run -d emulator-5554
```

---

## 🔧 配置说明

### 后端 URL 配置

在 `front/lib/screens/data_analysis_screen.dart` 中：

```dart
// 本地开发
static const String backendUrl = 'http://localhost:8080';

// 生产环境
static const String backendUrl = 'https://data-science-44398.an.r.appspot.com';
```

在 `front/lib/services/api_service.dart` 中：

```dart
static const String _baseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8080', // 本地开发
);
```

---

## 📊 新功能概览

### 1. 数据质量评估

**后端 API**: `/api/analysis/analyze-csv`

**前端组件**: `QualityDashboard`

**功能**:

- 质量分数 (0-100)
- 缺失值分析
- 异常值检测（IQR方法）
- 重复数据检查
- 智能建议

### 2. 相关性分析

**前端组件**: `CorrelationMatrixView`

**功能**:

- Pearson 相关系数
- Spearman 相关系数
- p-value 显著性检验
- 高相关性警告 (|r|>0.7)
- 多重共线性建议

### 3. 统计检验

**前端组件**: `StatisticalPanel`

**功能**:

- 正态性检验（Shapiro-Wilk / D'Agostino-Pearson）
- 偏度和峰度计算
- 数据转换建议
- 非参数方法推荐

---

## 🎯 响应式布局

### 移动端 (< 800px)

垂直布局顺序：

1. 质量仪表板
2. 基本信息
3. 统计检验面板
4. 相关性矩阵
5. 数据预览

### 桌面端 (≥ 800px)

分栏布局：

- **左侧 (30%)**: 质量仪表板 + 基本信息
- **右侧 (70%)**: 统计检验面板 + 相关性矩阵
- **底部 (100%)**: 数据预览

---

## 🧪 测试流程

### 1. 完整测试流程

```bash
# 1. 启动后端
cd "/Users/achilles/Documents/code/data science"
source venv/bin/activate
python back/main.py

# 2. 新终端启动前端
cd "/Users/achilles/Documents/code/data science/front"
flutter run -d chrome
```

### 2. 测试数据准备

创建测试 CSV 文件 `test_data.csv`：

```csv
age,income,score,category
25,50000,85,A
30,60000,90,B
35,70000,75,A
28,55000,88,B
40,80000,92,C
```

### 3. 测试步骤

1. **登录**: 使用 Google 或邮箱登录
2. **上传文件**: 选择 `test_data.csv`
3. **开始分析**: 点击"开始分析"按钮
4. **查看结果**:
   - 检查质量分数
   - 查看相关性矩阵
   - 查看统计检验结果

---

## 📦 完整的 API 响应结构

```json
{
  "success": true,
  "analysis_result": {
    "basic_info": {
      "rows": 100,
      "columns": 4,
      "column_names": ["age", "income", "score", "category"],
      "column_types": {
        "age": "int64",
        "income": "float64",
        "score": "int64",
        "category": "object"
      }
    },
    "preview": [...],
    "quality_analysis": {
      "success": true,
      "quality_score": 92.22,
      "missing_analysis": {...},
      "outlier_detection": {...},
      "recommendations": [...]
    },
    "correlations": {
      "success": true,
      "correlations": [...],
      "high_correlations": [...],
      "pearson_matrix": {...},
      "suggestions": [...]
    },
    "statistical_tests": {
      "success": true,
      "normality_tests": {...},
      "non_normal_columns": [...],
      "suggestions": [...]
    }
  },
  "performance": {
    "load_time": 0.15,
    "basic_analysis_time": 0.23,
    "total_time": 1.45
  }
}
```

---

## 🐛 常见问题

### 问题 1: `ModuleNotFoundError: No module named 'scipy'`

**解决方案**:

```bash
source venv/bin/activate
pip install scipy==1.11.4
```

### 问题 2: Flutter 依赖冲突

**解决方案**:

```bash
cd front
flutter clean
flutter pub get
```

### 问题 3: 后端 CORS 错误

**解决方案**: 确保 `back/main.py` 中有 CORS 配置：

```python
from flask_cors import CORS
CORS(app)
```

### 问题 4: 数据无法加载

**检查清单**:

1. ✅ 后端是否运行在 `http://localhost:8080`
2. ✅ 前端 API URL 配置是否正确
3. ✅ Firebase 认证是否成功
4. ✅ 文件是否成功上传到 GCS

---

## 🚀 部署到生产环境

### 后端部署 (Google App Engine)

```bash
cd "/Users/achilles/Documents/code/data science"

# 确保 requirements.txt 包含 scipy
# 确保 app.yaml 配置正确

gcloud app deploy

# 获取部署 URL
gcloud app browse
```

### 前端部署 (Firebase Hosting)

```bash
cd front

# 构建 Web 版本
flutter build web

# 部署到 Firebase
firebase deploy --only hosting
```

---

## 📚 文档资源

- **功能详解**: `docs/ENHANCED_ANALYSIS_GUIDE.md`
- **API 集成**: `docs/API_INTEGRATION_EXAMPLE.md`
- **快速参考**: `QUICK_REFERENCE.md`
- **实现总结**: `IMPLEMENTATION_SUMMARY.md`

---

## ✨ 主要改进点

### 后端

1. ✅ 集成 3 个新分析方法
2. ✅ 容错处理机制
3. ✅ 性能监控（耗时记录）
4. ✅ 详细的日志记录

### 前端

1. ✅ 强类型数据模型
2. ✅ 模块化组件架构
3. ✅ 响应式布局
4. ✅ 美观的可视化界面
5. ✅ 错误处理和加载状态

---

## 🎓 开发团队建议

### 本地开发工作流

```bash
# Terminal 1: 后端
cd "/Users/achilles/Documents/code/data science"
source venv/bin/activate
python back/main.py

# Terminal 2: 前端 (热重载)
cd "/Users/achilles/Documents/code/data science/front"
flutter run -d chrome

# Terminal 3: 日志监控
tail -f back/logs/app.log  # 如果有日志文件
```

### 代码质量检查

```bash
# Flutter 代码分析
cd front
flutter analyze

# Python 代码检查
cd back
python -m pylint services/
```

---

## 📊 性能指标

### 预期性能

| 数据规模 | 加载时间 | 分析时间 | 总时间 |
|---------|---------|---------|--------|
| < 1K 行 | < 0.2s  | < 0.5s  | < 1s   |
| 1K-10K  | < 0.5s  | < 2s    | < 3s   |
| 10K-50K | < 2s    | < 5s    | < 8s   |

---

## 🎉 完成检查清单

- [x] 后端 API 升级完成
- [x] scipy 依赖已添加
- [x] Dart 数据模型已创建
- [x] 三个可视化组件已创建
- [x] 响应式布局已实现
- [x] API Service 已更新
- [x] 主屏幕已重构
- [x] pubspec.yaml 已更新
- [x] 测试文件已创建
- [x] 文档已完善

---

## 📞 支持

如遇问题，请查看：

1. 日志文件（后端）
2. Flutter DevTools（前端）
3. 浏览器控制台（Web）
4. 相关文档

**状态**: ✅ 生产就绪  
**版本**: v2.0.0  
**最后更新**: 2024
