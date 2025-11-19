# 📁 完整项目结构

## 项目树形图

```
data-science/
│
├── 📄 README.md                    # 项目总览
├── 📄 QUICKSTART.md                # 快速开始指南
├── 📄 .env.example                 # 环境变量模板
├── 📄 .gitignore                   # Git忽略配置 ✨ 已优化
│
├── 📂 back/                        # 后端服务 (Python/Flask)
│   ├── 📄 main.py                  # Flask应用入口 ✨ 已集成中间件
│   ├── 📄 config.py                # 配置管理
│   ├── 📄 app.yaml                 # GAE部署配置
│   ├── 📄 requirements.txt         # Python依赖 ✨ 已更新
│   ├── 📄 pytest.ini               # ✨ 新增：Pytest配置
│   ├── 📄 .gcloudignore            # GAE忽略配置
│   │
│   ├── 📂 api/                     # API路由层
│   │   ├── __init__.py
│   │   ├── auth.py                 # 认证API
│   │   └── data.py                 # 数据处理API
│   │
│   ├── 📂 services/                # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── firebase_service.py    # Firebase认证服务
│   │   └── storage_service.py     # Cloud Storage服务
│   │
│   ├── 📂 models/                  # 数据模型层
│   │   ├── __init__.py
│   │   └── 📄 schemas.py           # ✨ 新增：API数据模型
│   │
│   ├── 📂 middleware/              # ✨ 新增：中间件
│   │   ├── __init__.py
│   │   ├── 📄 logging.py           # 日志中间件
│   │   └── 📄 rate_limit.py        # 限流中间件
│   │
│   ├── 📂 utils/                   # 工具函数
│   │   ├── __init__.py
│   │   ├── 📄 exceptions.py        # ✨ 新增：自定义异常
│   │   └── 📄 validators.py        # ✨ 新增：数据验证
│   │
│   └── 📂 tests/                   # ✨ 新增：测试模块
│       ├── 📄 conftest.py          # Pytest配置
│       └── 📄 test_auth.py         # 认证测试示例
│
├── 📂 front/                       # 前端应用 (Flutter)
│   ├── 📄 pubspec.yaml             # Flutter依赖配置
│   ├── 📄 firebase.json            # Firebase配置
│   ├── 📄 .firebaserc              # Firebase项目配置
│   │
│   ├── 📂 lib/                     # Dart源代码
│   │   ├── 📄 main.dart            # 应用入口
│   │   ├── 📄 firebase_options.dart # Firebase配置
│   │   │
│   │   ├── 📂 config/              # ✨ 新增：配置管理
│   │   │   └── 📄 constants.dart   # 应用常量
│   │   │
│   │   ├── 📂 models/              # 数据模型
│   │   │   ├── 📄 user.dart        # ✨ 新增：用户模型
│   │   │   └── 📄 api_response.dart # ✨ 新增：API响应模型
│   │   │
│   │   ├── 📂 screens/             # 页面组件
│   │   │   └── 📄 login_screen.dart
│   │   │
│   │   ├── 📂 services/            # 服务层
│   │   │   ├── 📄 auth_service.dart
│   │   │   └── 📄 api_service.dart
│   │   │
│   │   ├── 📂 utils/               # ✨ 新增：工具类
│   │   │   └── 📄 error_handler.dart
│   │   │
│   │   └── 📂 widgets/             # 可复用组件
│   │       └── 📄 loading_overlay.dart # ✨ 新增
│   │
│   ├── 📂 web/                     # Web配置
│   ├── 📂 android/                 # Android配置
│   ├── 📂 ios/                     # iOS配置
│   └── 📂 test/                    # 测试文件
│
├── 📂 data/                        # 数据文件目录
│   ├── 📄 README.md                # ✨ 新增：数据目录使用指南
│   ├── 📂 raw/                     # 原始数据
│   ├── 📂 processed/               # 处理后数据
│   ├── 📂 models/                  # 训练模型（.gitignore）
│   └── 📂 results/                 # 实验结果
│
├── 📂 scripts/                     # 脚本工具
│   ├── 📄 deploy_backend.sh        # 后端部署脚本
│   ├── 📄 deploy_frontend.sh       # 前端部署脚本
│   ├── 📄 setup_gcp.sh             # GCP初始化脚本
│   └── 📄 sync_data.py             # ✨ 新增：数据同步脚本
│
├── 📂 docs/                        # 项目文档
│   ├── 📄 api.md                   # API文档
│   ├── 📄 architecture.md          # 架构设计
│   ├── 📄 deployment.md            # 部署指南
│   ├── 📄 frontend-backend-integration.md # 集成指南
│   └── 📄 OPTIMIZATION_SUMMARY.md  # ✨ 新增：优化总结
│
└── 📂 .vscode/                     # ✨ 新增：VSCode配置
    ├── 📄 settings.json            # 编辑器设置
    ├── 📄 launch.json              # 调试配置
    └── 📄 tasks.json               # 任务配置
```

## 📊 统计信息

### 后端结构

- **API端点**: 2个蓝图 (auth, data)
- **服务**: 2个服务 (firebase, storage)
- **中间件**: 2个 (logging, rate_limit) ✨
- **工具模块**: 2个 (exceptions, validators) ✨
- **测试文件**: 配置完成 ✨

### 前端结构

- **页面**: 1个 (login)
- **服务**: 2个 (auth, api)
- **模型**: 2个 (user, api_response) ✨
- **工具**: 1个 (error_handler) ✨
- **组件**: 1个 (loading_overlay) ✨

### 配置文件

- **环境配置**: .env, .env.example
- **部署配置**: app.yaml, firebase.json
- **IDE配置**: .vscode/* ✨
- **测试配置**: pytest.ini ✨

## 🎯 技术栈总览

### 前端

| 类型 | 技术 | 用途 |
|------|------|------|
| 框架 | Flutter Web | 跨平台UI框架 |
| 状态管理 | Provider (推荐) | 状态管理 |
| 认证 | Firebase Auth | 用户认证 |
| HTTP | http package | API调用 |
| 部署 | Firebase Hosting | 静态网站托管 |

### 后端

| 类型 | 技术 | 用途 |
|------|------|------|
| 框架 | Flask 3.0 | Web框架 |
| WSGI | Gunicorn | 生产服务器 |
| 认证 | Firebase Admin SDK | Token验证 |
| 存储 | Cloud Storage | 文件存储 |
| 测试 | Pytest | 单元测试 |
| 部署 | Google App Engine | PaaS平台 |

### 数据科学

| 类型 | 技术 | 用途 |
|------|------|------|
| 数据处理 | pandas | 数据分析 |
| 机器学习 | scikit-learn | ML模型 |
| 数值计算 | numpy | 科学计算 |
| 可视化 | matplotlib | 数据可视化 |

### DevOps

| 类型 | 技术 | 用途 |
|------|------|------|
| 版本控制 | Git | 代码管理 |
| CI/CD | (待配置) | 自动化部署 |
| 日志 | Cloud Logging | 日志收集 |
| 监控 | Cloud Monitoring | 性能监控 |

## 🔗 模块依赖关系

### 后端依赖流

```
main.py
  ├─→ config.py (配置)
  ├─→ middleware/* (中间件) ✨
  │   ├─→ logging.py
  │   └─→ rate_limit.py
  ├─→ utils/exceptions.py (错误处理) ✨
  ├─→ api/* (路由)
  │   ├─→ auth.py
  │   └─→ data.py
  └─→ services/* (业务逻辑)
      ├─→ firebase_service.py
      └─→ storage_service.py
          └─→ utils/validators.py ✨
```

### 前端依赖流

```
main.dart
  ├─→ config/constants.dart (配置) ✨
  ├─→ firebase_options.dart
  ├─→ screens/*
  │   └─→ login_screen.dart
  │       ├─→ services/auth_service.dart
  │       ├─→ services/api_service.dart
  │       ├─→ utils/error_handler.dart ✨
  │       └─→ widgets/loading_overlay.dart ✨
  └─→ models/* ✨
      ├─→ user.dart
      └─→ api_response.dart
```

## 📝 关键文件说明

### 配置文件

- **`.env`**: 环境变量（不提交）
- **`.env.example`**: 环境变量模板
- **`back/config.py`**: 后端配置类
- **`front/lib/config/constants.dart`**: 前端常量 ✨

### 入口文件

- **`back/main.py`**: Flask应用入口
- **`front/lib/main.dart`**: Flutter应用入口

### 部署文件

- **`back/app.yaml`**: GAE部署配置
- **`front/firebase.json`**: Firebase Hosting配置

### 开发工具

- **`.vscode/*`**: VSCode配置 ✨
- **`back/pytest.ini`**: 测试配置 ✨
- **`scripts/sync_data.py`**: 数据同步工具 ✨

## 🚀 快速命令

### 开发

```bash
# 后端
cd back && python main.py

# 前端  
cd front && flutter run -d chrome

# 测试
cd back && pytest -v
```

### 部署

```bash
# 后端
cd back && gcloud app deploy

# 前端
cd front && flutter build web && firebase deploy
```

### 数据同步

```bash
# 下载
python scripts/sync_data.py --download

# 上传
python scripts/sync_data.py --upload
```

---

✨ **标记说明**: 带有 ✨ 的项目为本次优化新增或重要改进的内容
