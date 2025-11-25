# ⚡ 智能能源管理与数据科学平台

> **Energy Management & Data Science Platform**
>
> 一个基于机器学习和数学优化的智能能源调度系统，采用全栈云原生架构

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![Flutter](https://img.shields.io/badge/Flutter-3.10+-blue.svg)](https://flutter.dev)
[![GCP](https://img.shields.io/badge/Google%20Cloud-Platform-4285F4.svg)](https://cloud.google.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📋 目录

- [项目概述](#-项目概述)
- [核心功能](#-核心功能)
- [系统架构](#-系统架构)
- [技术栈详解](#-技术栈详解)
- [项目结构](#-项目结构)
- [快速开始](#-快速开始)
- [API 文档](#-api-文档)
- [部署指南](#-部署指南)
- [开发指南](#-开发指南)
- [测试](#-测试)
- [贡献指南](#-贡献指南)

---

## 🎯 项目概述

本项目是一个**智能能源管理平台**，旨在帮助用户优化电池储能系统的充放电调度，实现电费节省和能源效率最大化。

### 🌟 项目亮点

| 特性 | 描述 |
|------|------|
| 🤖 **机器学习预测** | 使用随机森林模型预测未来 24 小时能源负载 |
| 📊 **数学优化** | 基于 Gurobi 求解器的混合整数规划 (MIP) 优化 |
| 🌐 **实时数据** | 集成 CAISO 电网数据和 OpenWeatherMap 天气 API |
| ☁️ **云原生架构** | 完全部署在 Google Cloud Platform |
| 🐳 **容器化** | 支持 Docker 部署，可移植到任何容器平台 |
| 📱 **跨平台前端** | Flutter Web 响应式设计，支持桌面和移动端 |

### 📈 业务价值

- **电费节省**: 通过智能调度，在低谷时段充电、高峰时段放电
- **负载预测**: 基于历史数据和天气信息预测用电需求
- **数据分析**: 支持用户上传 CSV 数据进行统计分析
- **决策支持**: 可视化优化结果，支持 What-If 场景模拟

---

## 🚀 核心功能

### 1. 能源优化调度 ⚡

基于混合整数规划 (MIP) 的电池储能优化系统：

```
目标函数: 最小化总购电成本
约束条件:
  - 电池容量约束 (SOC 0%-100%)
  - 充放电功率约束
  - 充放电效率损耗
  - 能量守恒方程
```

**支持参数配置:**

- 电池容量 (kWh)
- 最大充放电功率 (kW)
- 充放电效率
- 初始电量状态 (SOC)
- 目标优化日期

### 2. 负载预测 🔮

使用随机森林回归模型预测未来能源需求：

**特征工程:**

- 时间特征: 小时、星期几
- 环境特征: 温度
- 价格特征: 峰谷电价

**模型指标:**

- MAE (平均绝对误差)
- RMSE (均方根误差)
- R² Score

### 3. 数据分析 📊

支持用户上传 CSV 文件进行全面的数据分析：

- **描述性统计**: 均值、标准差、分位数等
- **数据质量检查**: 缺失值、异常值检测
- **相关性分析**: Pearson/Spearman 相关系数矩阵
- **统计检验**: 正态性检验、时间序列平稳性检验

### 4. 实时数据管道 🌐

自动获取外部数据源：

| 数据源 | 类型 | 更新频率 |
|--------|------|----------|
| CAISO | 加州电网负载数据 | 每小时 |
| OpenWeatherMap | 洛杉矶天气数据 | 每小时 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          用户层 (User Layer)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │              Flutter Web Application                         │   │
│   │  ┌─────────┐ ┌─────────────┐ ┌──────────┐ ┌─────────────┐   │   │
│   │  │ 登录页面 │ │ 数据分析页面 │ │ 优化页面 │ │ 历史记录页面 │   │   │
│   │  └─────────┘ └─────────────┘ └──────────┘ └─────────────┘   │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                    Firebase Auth (ID Token)                         │
│                              ▼                                      │
├─────────────────────────────────────────────────────────────────────┤
│                          API 网关层                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │              Flask REST API (Google App Engine)              │   │
│   │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │   │
│   │  │ /auth   │ │ /data    │ │/analysis │ │ /optimization    │ │   │
│   │  └─────────┘ └──────────┘ └──────────┘ └──────────────────┘ │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
├─────────────────────────────────────────────────────────────────────┤
│                          服务层 (Service Layer)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐     │
│   │ AnalysisService│ │  MLService   │ │ OptimizationService  │     │
│   │  (Pandas/SciPy)│ │(Scikit-learn)│ │     (Gurobi MIP)     │     │
│   └───────────────┘ └───────────────┘ └───────────────────────┘     │
│                                                                     │
│   ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐     │
│   │ StorageService│ │FirebaseService│ │ExternalDataService   │     │
│   │     (GCS)     │ │  (Firestore)  │ │ (CAISO/Weather API)  │     │
│   └───────────────┘ └───────────────┘ └───────────────────────┘     │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                          数据层 (Data Layer)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│   │ Cloud Storage   │  │  Firestore   │  │  External APIs     │     │
│   │ (文件/模型存储)  │  │ (用户数据/历史)│  │ (CAISO/Weather)   │     │
│   └─────────────────┘  └──────────────┘  └────────────────────┘     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 技术栈详解

### 后端技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **Web 框架** | Flask | 3.0.0 | RESTful API 服务 |
| **WSGI 服务器** | Gunicorn | 21.2.0 | 生产环境部署 |
| **跨域处理** | Flask-CORS | 4.0.0 | CORS 支持 |
| **数据处理** | Pandas | ≥1.5.3 | 数据分析与处理 |
| **数值计算** | NumPy | ≥1.26.2 | 数值计算 |
| **科学计算** | SciPy | ≥1.11.4 | 统计检验 |
| **机器学习** | Scikit-learn | 1.3.2 | 随机森林模型 |
| **优化求解** | Gurobi | 10.0.3 | 混合整数规划 |
| **实时数据** | GridStatus | ≥0.26.0 | CAISO 电网数据 |
| **任务调度** | APScheduler | 3.10.4 | 定时任务 |
| **云服务** | Firebase Admin | 6.5.0 | 认证与存储 |

### 前端技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **框架** | Flutter | ≥3.10.0 | 跨平台 UI |
| **认证** | Firebase Auth | 6.1.2 | 用户认证 |
| **HTTP** | http | 1.1.0 | API 调用 |
| **文件选择** | file_picker | 8.0.0 | 文件上传 |
| **图表** | fl_chart | 1.1.1 | 数据可视化 |
| **进度指示** | percent_indicator | 4.2.3 | 进度展示 |
| **国际化** | intl | 0.20.2 | 日期格式化 |

### 云平台与基础设施

| 服务 | 用途 |
|------|------|
| **Google App Engine** | 后端 API 托管 (Serverless) |
| **Firebase Hosting** | 前端静态资源托管 |
| **Firebase Authentication** | 用户身份认证 (Google/Email) |
| **Cloud Storage** | 文件存储 (CSV/模型文件) |
| **Cloud Firestore** | NoSQL 数据库 (用户数据/历史记录) |
| **Cloud Scheduler** | 定时任务触发 (GAE Cron) |

### DevOps 工具链

| 工具 | 用途 |
|------|------|
| **Docker** | 容器化部署 |
| **Docker Compose** | 本地开发环境编排 |
| **pytest** | Python 单元测试 |
| **gcloud CLI** | GCP 部署管理 |
| **Firebase CLI** | Firebase 部署管理 |

---

## 📁 项目结构

```
data-science/
├── 📂 back/                          # 后端服务 (Python/Flask)
│   ├── 📂 api/                       # API 路由层
│   │   ├── auth.py                   # 认证 API (/api/auth/*)
│   │   ├── data.py                   # 数据管理 API (/api/data/*)
│   │   ├── analysis.py               # 数据分析 API (/api/analysis/*)
│   │   ├── optimization.py           # 优化调度 API (/api/optimization/*)
│   │   ├── history.py                # 历史记录 API (/api/history/*)
│   │   └── ml.py                     # 机器学习 API (预留)
│   │
│   ├── 📂 services/                  # 业务逻辑层
│   │   ├── analysis_service.py       # 数据分析服务 (Pandas/SciPy)
│   │   ├── ml_service.py             # 机器学习服务 (Scikit-learn)
│   │   ├── optimization_service.py   # 优化服务 (Gurobi MIP)
│   │   ├── firebase_service.py       # Firebase 认证服务
│   │   ├── storage_service.py        # Cloud Storage 服务
│   │   ├── history_service.py        # 历史记录服务
│   │   ├── external_data_service.py  # 外部数据服务 (CAISO/Weather)
│   │   └── data_processor.py         # 数据预处理服务
│   │
│   ├── 📂 middleware/                # 中间件
│   │   ├── logging.py                # 日志中间件
│   │   └── rate_limit.py             # 限流中间件
│   │
│   ├── 📂 models/                    # 模型文件
│   │   ├── schemas.py                # 数据模型定义
│   │   └── rf_model.joblib           # 随机森林模型 (gitignore)
│   │
│   ├── 📂 utils/                     # 工具函数
│   │   ├── exceptions.py             # 自定义异常
│   │   └── validators.py             # 数据验证器
│   │
│   ├── 📂 tests/                     # 测试文件
│   │   ├── conftest.py               # pytest 配置
│   │   └── test_auth.py              # 认证测试
│   │
│   ├── main.py                       # Flask 应用入口
│   ├── config.py                     # 配置管理
│   ├── scheduler.py                  # 定时任务调度器
│   ├── requirements.txt              # Python 依赖
│   ├── app.yaml                      # GAE 部署配置
│   ├── Dockerfile                    # Docker 镜像定义
│   ├── .dockerignore                 # Docker 忽略文件
│   └── .env.example                  # 环境变量模板
│
├── 📂 front/                         # 前端应用 (Flutter)
│   ├── 📂 lib/
│   │   ├── 📂 screens/               # 页面
│   │   │   ├── login_screen.dart             # 登录页面
│   │   │   ├── data_analysis_screen.dart     # 数据分析页面
│   │   │   ├── modeling_screen.dart          # 能源优化页面
│   │   │   ├── history_screen.dart           # 历史记录页面
│   │   │   └── analysis_detail_screen.dart   # 分析详情页面
│   │   │
│   │   ├── 📂 services/              # 服务层
│   │   │   ├── api_service.dart      # API 调用封装
│   │   │   └── auth_service.dart     # 认证服务
│   │   │
│   │   ├── 📂 models/                # 数据模型
│   │   │   ├── analysis_result.dart          # 分析结果模型
│   │   │   └── optimization_result.dart      # 优化结果模型
│   │   │
│   │   ├── 📂 widgets/               # 可复用组件
│   │   │   ├── 📂 analysis/          # 分析相关组件
│   │   │   │   ├── quality_dashboard.dart    # 质量仪表盘
│   │   │   │   ├── correlation_matrix_view.dart
│   │   │   │   └── statistical_panel.dart
│   │   │   ├── main_navigation.dart          # 主导航
│   │   │   ├── power_chart_widget.dart       # 功率图表
│   │   │   ├── soc_chart_widget.dart         # SOC 图表
│   │   │   ├── responsive_wrapper.dart       # 响应式包装器
│   │   │   └── loading_overlay.dart          # 加载遮罩
│   │   │
│   │   ├── 📂 config/                # 配置
│   │   │   └── constants.dart        # 常量定义
│   │   │
│   │   ├── 📂 utils/                 # 工具
│   │   │   └── responsive_helper.dart # 响应式辅助
│   │   │
│   │   ├── main.dart                 # 应用入口
│   │   └── firebase_options.dart     # Firebase 配置
│   │
│   ├── 📂 web/                       # Web 平台配置
│   ├── 📂 android/                   # Android 平台配置
│   ├── 📂 ios/                       # iOS 平台配置
│   ├── pubspec.yaml                  # Flutter 依赖
│   └── firebase.json                 # Firebase Hosting 配置
│
├── 📂 data/                          # 数据目录 (gitignore)
│   ├── 📂 raw/                       # 原始数据 (2018-2019 楼层能源数据)
│   ├── 📂 processed/                 # 处理后的数据
│   ├── 📂 models/                    # 训练好的模型
│   └── 📂 output/                    # 优化输出结果
│
├── 📂 scripts/                       # 运维脚本
│   ├── deploy_backend.sh             # 后端部署脚本
│   ├── deploy_frontend.sh            # 前端部署脚本
│   ├── setup_gcp.sh                  # GCP 初始化脚本
│   └── sync_data.py                  # 数据同步脚本
│
├── 📂 notebooks/                     # Jupyter 笔记本 (数据探索)
├── 📂 reports/                       # 分析报告
│
├── docker-compose.yml                # Docker 编排配置
├── Dockerfile.frontend               # 前端 Docker 镜像
├── nginx.conf                        # Nginx 配置 (前端)
├── .gitignore                        # Git 忽略规则
├── .dockerignore                     # Docker 忽略规则
├── README.md                         # 项目文档 (本文件)
└── README_DOCKER.md                  # Docker 部署文档
```

---

## 🚀 快速开始

### 环境要求

| 工具 | 最低版本 | 说明 |
|------|----------|------|
| Python | 3.11+ | 后端运行时 |
| Flutter | 3.10+ | 前端开发 |
| Docker | 20.10+ | 容器化部署 (可选) |
| Node.js | 18+ | Firebase CLI |
| gcloud CLI | 最新 | GCP 部署 |

### 方式一：本地开发

#### 1. 克隆项目

```bash
git clone https://github.com/WssAchilles/maccode.git
cd "data science"
```

#### 2. 后端设置

```bash
# 进入后端目录
cd back

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的配置

# 启动开发服务器
python main.py
```

#### 3. 前端设置

```bash
# 进入前端目录
cd front

# 获取依赖
flutter pub get

# 启动开发服务器
flutter run -d chrome
```

### 方式二：Docker 部署

```bash
# 配置环境变量
cp back/.env.example back/.env
# 编辑 back/.env 文件

# 构建并启动所有服务
docker compose up --build

# 访问应用
# 前端: http://localhost:3000
# 后端: http://localhost:8080
```

### 方式三：云端部署

详见 [部署指南](#-部署指南) 章节。

---

## 📚 API 文档

### 基础信息

| 项目 | 值 |
|------|-----|
| 基础 URL | `https://data-science-44398.an.r.appspot.com` |
| API 版本 | v1 |
| 认证方式 | Firebase ID Token (Bearer) |
| 内容类型 | application/json |

### 认证相关

#### 验证 Token

```http
POST /api/auth/verify
Authorization: Bearer <Firebase ID Token>
```

**响应示例:**

```json
{
  "success": true,
  "user": {
    "uid": "abc123",
    "email": "user@example.com",
    "email_verified": true
  }
}
```

#### 获取用户资料

```http
GET /api/auth/profile
Authorization: Bearer <Firebase ID Token>
```

### 数据管理

#### 获取上传 URL

```http
POST /api/data/upload-url
Authorization: Bearer <Firebase ID Token>
Content-Type: application/json

{
  "fileName": "data.csv",
  "contentType": "text/csv"
}
```

**响应示例:**

```json
{
  "success": true,
  "upload_url": "https://storage.googleapis.com/...",
  "storage_path": "uploads/uid/data.csv"
}
```

#### 列出用户文件

```http
GET /api/data/list
Authorization: Bearer <Firebase ID Token>
```

### 数据分析

#### 分析 CSV 文件

```http
POST /api/analysis/analyze-csv
Authorization: Bearer <Firebase ID Token>
Content-Type: application/json

{
  "storage_path": "uploads/uid/data.csv",
  "filename": "data.csv"
}
```

**响应示例:**

```json
{
  "success": true,
  "analysis_result": {
    "basic_info": {
      "rows": 8760,
      "columns": 10,
      "column_names": ["Timestamp", "Load", "Temperature", ...],
      "column_types": {"Timestamp": "datetime64", "Load": "float64", ...}
    },
    "descriptive_stats": {
      "statistics": {
        "Load": {"mean": 198.42, "std": 56.78, "min": 113.05, "max": 380.32, ...}
      }
    },
    "quality_analysis": {
      "missing_percentage": 0.5,
      "duplicate_rows": 0,
      "outliers": {...}
    },
    "correlations": {
      "pearson": {...},
      "spearman": {...}
    },
    "statistical_tests": {
      "normality": {...},
      "stationarity": {...}
    }
  }
}
```

### 能源优化

#### 执行优化调度

```http
POST /api/optimization/run
Authorization: Bearer <Firebase ID Token>
Content-Type: application/json

{
  "initial_soc": 0.5,
  "target_date": "2024-11-24",
  "battery_capacity": 5000,
  "battery_power": 2000,
  "temperature_forecast": [24.0, 23.5, ...]
}
```

**响应示例:**

```json
{
  "success": true,
  "optimization": {
    "status": "Optimal",
    "chart_data": [
      {
        "hour": 0,
        "datetime": "2024-11-24T00:00:00",
        "load": 20542.0,
        "price": 0.3,
        "battery_action": 2000.0,
        "charge_power": 2000.0,
        "discharge_power": 0.0,
        "soc": 53.68,
        "grid_power": 22542.0
      }
    ],
    "summary": {
      "total_cost_without_battery": 125602.57,
      "total_cost_with_battery": 124891.88,
      "savings": 710.69,
      "savings_percent": 0.57,
      "total_load": 476199.0,
      "total_charged": 7110.0,
      "total_discharged": 6541.0,
      "peak_load": 38032.0,
      "min_load": 11305.0
    },
    "strategy": {
      "charging_hours": [0, 1, 2, 3, 4, 5],
      "discharging_hours": [18, 19, 20, 21],
      "charging_count": 6,
      "discharging_count": 4
    }
  },
  "prediction": {
    "target_date": "2024-11-24",
    "avg_load": 19841.63,
    "peak_load": 38032.0,
    "min_load": 11305.0
  },
  "battery_config": {
    "capacity": 5000,
    "max_power": 2000,
    "efficiency": 0.92
  }
}
```

### 历史记录

#### 获取分析历史

```http
GET /api/history/analyses?limit=10
Authorization: Bearer <Firebase ID Token>
```

#### 获取优化历史

```http
GET /api/history/optimizations?limit=10
Authorization: Bearer <Firebase ID Token>
```

### 健康检查

```http
GET /health
```

**响应:**

```json
{
  "status": "ok",
  "timestamp": "2024-11-24T12:00:00Z"
}
```

---

## 🚢 部署指南

### Google Cloud Platform 部署

#### 前置条件

1. 创建 GCP 项目
2. 启用以下 API:
   - App Engine Admin API
   - Cloud Storage API
   - Cloud Firestore API
   - Cloud Scheduler API

3. 安装并配置 gcloud CLI:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

#### 部署后端到 App Engine

```bash
cd back

# 部署应用
gcloud app deploy app.yaml

# 部署定时任务 (可选)
gcloud app deploy cron.yaml
```

**`app.yaml` 配置说明:**

```yaml
runtime: python311
entrypoint: gunicorn -b :$PORT --timeout 300 --workers 1 main:app

instance_class: F4  # 高性能实例

automatic_scaling:
  min_instances: 0    # 无流量时自动缩容到 0
  max_instances: 1    # 限制最大实例数控制成本

env_variables:
  GCP_PROJECT_ID: "your-project-id"
  STORAGE_BUCKET_NAME: "your-bucket.appspot.com"
  GRB_LICENSEID: "your-license-id"
  GRB_WLSACCESSID: "your-access-id"
  GRB_WLSSECRET: "your-secret"
```

#### 部署前端到 Firebase Hosting

```bash
cd front

# 构建 Web 版本
flutter build web --release

# 部署到 Firebase Hosting
firebase deploy --only hosting
```

### Docker 部署

详见 [README_DOCKER.md](README_DOCKER.md)。

#### 部署到 Cloud Run

```bash
# 构建镜像
cd back
gcloud builds submit --tag gcr.io/YOUR_PROJECT/backend

# 部署到 Cloud Run
gcloud run deploy backend \
  --image gcr.io/YOUR_PROJECT/backend \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars "GRB_LICENSEID=xxx,GRB_WLSACCESSID=xxx,GRB_WLSSECRET=xxx"
```

---

## 👨‍💻 开发指南

### 代码规范

#### Python (后端)

- 遵循 [PEP 8](https://pep8.org/) 代码规范
- 使用 Type Hints 进行类型注解
- 文档字符串使用 Google Style

```python
def analyze_data(df: pd.DataFrame, filename: str) -> Dict[str, Any]:
    """
    分析 DataFrame 数据。
    
    Args:
        df: 输入的 Pandas DataFrame
        filename: 文件名
        
    Returns:
        包含分析结果的字典
        
    Raises:
        ValidationError: 数据验证失败时
    """
    pass
```

#### Dart (前端)

- 遵循 [Dart 风格指南](https://dart.dev/guides/language/effective-dart/style)
- 使用 `flutter_lints` 进行代码检查
- 组件命名使用 PascalCase

```dart
/// 能源优化仪表盘
/// 
/// 展示优化结果和交互式参数配置
class ModelingScreen extends StatefulWidget {
  const ModelingScreen({super.key});
  
  @override
  State<ModelingScreen> createState() => _ModelingScreenState();
}
```

### 分支策略

| 分支 | 用途 |
|------|------|
| `main` | 生产环境代码 |
| `develop` | 开发环境代码 |
| `feature/*` | 功能开发分支 |
| `hotfix/*` | 紧急修复分支 |

### 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: 添加能源优化功能
fix: 修复 CSV 解析错误
docs: 更新 API 文档
refactor: 重构分析服务
test: 添加单元测试
chore: 更新依赖版本
```

### 环境变量

#### 后端环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `GCP_PROJECT_ID` | ✅ | GCP 项目 ID |
| `STORAGE_BUCKET_NAME` | ✅ | Cloud Storage 存储桶名 |
| `GRB_LICENSEID` | ✅ | Gurobi 许可证 ID |
| `GRB_WLSACCESSID` | ✅ | Gurobi WLS Access ID |
| `GRB_WLSSECRET` | ✅ | Gurobi WLS Secret |
| `OPENWEATHER_API_KEY` | ⬜ | OpenWeatherMap API Key |
| `FLASK_ENV` | ⬜ | 环境模式 (development/production) |
| `SECRET_KEY` | ⬜ | Flask Secret Key |

#### 前端配置

前端配置位于 `front/lib/config/constants.dart`:

```dart
class AppConstants {
  static const String apiBaseUrl = 
    'https://data-science-44398.an.r.appspot.com';
  static const double defaultInitialSoc = 0.5;
  // ...
}
```

---

## 🧪 测试

### 后端测试

```bash
cd back

# 运行所有测试
pytest

# 运行并显示覆盖率
pytest --cov=. --cov-report=html

# 运行特定测试
pytest tests/test_auth.py -v
```

### 测试结构

```
back/tests/
├── conftest.py           # pytest 配置和 fixtures
├── test_auth.py          # 认证测试
├── test_analysis.py      # 分析服务测试
├── test_optimization.py  # 优化服务测试
└── test_api.py           # API 集成测试
```

### 前端测试

```bash
cd front

# 运行单元测试
flutter test

# 运行集成测试
flutter test integration_test/
```

---

## 🔧 常见问题

### Q1: Gurobi 许可证错误?

确保已正确配置 WLS 环境变量:

```bash
export GRB_LICENSEID=your-license-id
export GRB_WLSACCESSID=your-access-id
export GRB_WLSSECRET=your-secret
```

### Q2: Firebase 认证失败?

1. 检查 Firebase 项目配置
2. 确保已启用 Google 登录提供商
3. 检查 OAuth 客户端 ID 配置

### Q3: CORS 错误?

检查后端 `config.py` 中的 `CORS_ORIGINS` 是否包含前端域名。

### Q4: 数据分析超时?

- 大文件 (>50MB) 可能需要更长时间
- GAE 默认超时 60 秒，已配置为 300 秒
- 考虑分割大文件或使用异步处理

---

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤:

1. Fork 本仓库
2. 创建功能分支: `git checkout -b feature/AmazingFeature`
3. 提交更改: `git commit -m 'feat: Add AmazingFeature'`
4. 推送分支: `git push origin feature/AmazingFeature`
5. 提交 Pull Request

### 开发环境设置

```bash
# 安装开发依赖
cd back
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 如果有的话

# 安装 pre-commit hooks (可选)
pre-commit install
```

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 📮 联系方式

- **项目维护者**: Achilles
- **GitHub**: [WssAchilles](https://github.com/WssAchilles)
- **项目地址**: [maccode](https://github.com/WssAchilles/maccode)

---

## 🙏 致谢

- [Google Cloud Platform](https://cloud.google.com/) - 云基础设施
- [Firebase](https://firebase.google.com/) - 认证与托管
- [Gurobi](https://www.gurobi.com/) - 优化求解器
- [Flutter](https://flutter.dev/) - 跨平台 UI 框架
- [CAISO](http://www.caiso.com/) - 电网数据
- [OpenWeatherMap](https://openweathermap.org/) - 天气数据

---

<p align="center">
  Made with ❤️ for Data Science
</p>
