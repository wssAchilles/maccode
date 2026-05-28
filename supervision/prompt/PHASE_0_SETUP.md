# Phase 0: 项目初始化

## 目标

搭建项目骨架，配置开发环境，建立代码质量基线。

复杂度：低 | 风险：低 | 预计时间：0.5-1 天

## 业务流

无独立业务流。本 Phase 为基础设施搭建。

## 目录结构

```
project/
├── pyproject.toml              # Python 项目配置
├── requirements.txt            # 生产依赖
├── requirements-dev.txt        # 开发依赖
├── .env.example                # 环境变量模板
├── .gitignore                  # Git 忽略规则
├── .pre-commit-config.yaml     # Pre-commit hooks
├── ruff.toml                   # Ruff 配置
├── mypy.ini                    # 类型检查配置
├── pytest.ini                  # 测试配置
├── docker-compose.yml          # Docker 编排
├── Makefile                    # 常用命令
├── shared/
│   ├── __init__.py
│   ├── configs/
│   │   ├── __init__.py
│   │   ├── settings.py         # 应用配置（pydantic-settings）
│   │   └── constants.py        # 全局常量
│   ├── exceptions/
│   │   ├── __init__.py
│   │   └── errors.py           # 自定义异常
│   └── schemas/
│       ├── __init__.py
│       └── common.py           # 共享 Schema
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures
│   ├── unit/
│   │   └── __init__.py
│   ├── integration/
│   │   └── __init__.py
│   └── e2e/
│       └── __init__.py
└── scripts/
    ├── setup.sh                # 环境初始化脚本
    └── benchmark.py            # 性能基准测试（骨架）
```

## 文件清单

### 1. pyproject.toml

| 项目 | 值 |
|---|---|
| 文件名 | pyproject.toml |
| 作用 | Python 项目元数据、依赖、工具配置 |
| 所属层 | shared |
| 依赖模块 | 无 |
| 耦合风险 | 无 |
| 未来扩展 | 添加新依赖、新工具配置 |
| 不能合并原因 | Python 项目标准入口文件 |

内容要点：
- 项目名称、版本、描述
- Python 版本要求（≥3.11）
- 生产依赖列表
- 开发依赖列表
- Ruff、mypy、pytest 配置引用

### 2. requirements.txt

| 项目 | 值 |
|---|---|
| 文件名 | requirements.txt |
| 作用 | 生产环境依赖锁定 |
| 所属层 | shared |
| 依赖模块 | 无 |
| 耦合风险 | 无 |
| 未来扩展 | 添加新依赖 |
| 不能合并原因 | Docker 构建需要 |

依赖列表：
- supervision>=0.25.0
- ultralytics>=8.0.0
- numpy>=1.24.0
- opencv-python>=4.8.0
- fastapi>=0.100.0
- uvicorn[standard]>=0.23.0
- websockets>=11.0
- pydantic>=2.0.0
- pydantic-settings>=2.0.0
- sqlalchemy>=2.0.0
- aiosqlite>=0.19.0
- openai>=1.0.0
- python-multipart>=0.0.6
- tqdm>=4.65.0
- structlog>=23.0.0

### 3. requirements-dev.txt

| 项目 | 值 |
|---|---|
| 文件名 | requirements-dev.txt |
| 作用 | 开发环境依赖锁定 |
| 所属层 | shared |
| 依赖模块 | 无 |
| 耦合风险 | 无 |
| 未来扩展 | 添加新开发工具 |
| 不能合并原因 | 与生产依赖分离 |

依赖列表：
- pytest>=7.0.0
- pytest-asyncio>=0.21.0
- pytest-cov>=4.0.0
- httpx>=0.24.0
- ruff>=0.1.0
- mypy>=1.5.0
- pre-commit>=3.0.0

### 4. .env.example

| 项目 | 值 |
|---|---|
| 文件名 | .env.example |
| 作用 | 环境变量模板，指导配置 |
| 所属层 | shared |
| 依赖模块 | 无 |
| 耦合风险 | 无 |
| 未来扩展 | 添加新环境变量 |
| 不能合并原因 | 安全考虑，不提交真实配置 |

变量分类：
- 应用配置：APP_ENV, APP_DEBUG, APP_HOST, APP_PORT
- 数据库：DATABASE_URL
- LLM：OPENAI_API_KEY, OPENAI_MODEL, LLM_ENABLED
- CV：YOLO_MODEL, YLOO_DEVICE, CONFIDENCE_THRESHOLD, IOU_THRESHOLD
- 日志：LOG_LEVEL, LOG_FORMAT

### 5. shared/configs/settings.py

| 项目 | 值 |
|---|---|
| 文件名 | shared/configs/settings.py |
| 作用 | 应用配置管理（pydantic-settings） |
| 所属层 | shared |
| 依赖模块 | [pydantic-settings] |
| 耦合风险 | 低 |
| 未来扩展 | 添加新配置项 |
| 不能合并原因 | 配置管理是独立关注点 |

配置类设计：
- `AppConfig`：应用基础配置
- `DatabaseConfig`：数据库配置
- `CVConfig`：CV 引擎配置
- `LLMConfig`：LLM 配置
- `Settings`：总配置类，组合上述配置

### 6. shared/configs/constants.py

| 项目 | 值 |
|---|---|
| 文件名 | shared/configs/constants.py |
| 作用 | 全局常量定义 |
| 所属层 | shared |
| 依赖模块 | 无 |
| 耦合风险 | 无 |
| 未来扩展 | 添加新常量 |
| 不能合并原因 | 集中管理常量 |

常量分类：
- 视频处理常量（默认 FPS、缓冲大小）
- 检测常量（默认置信度、IoU 阈值）
- 速度估算常量（最大速度、最小位移）
- API 常量（分页大小、最大上传大小）

### 7. shared/exceptions/errors.py

| 项目 | 值 |
|---|---|
| 文件名 | shared/exceptions/errors.py |
| 作用 | 自定义异常层次结构 |
| 所属层 | shared |
| 依赖模块 | 无 |
| 耦合风险 | 无 |
| 未来扩展 | 添加新异常类型 |
| 不能合并原因 | 异常是独立关注点 |

异常层次：
- `TrafficPerceptionError`（基类）
  - `CVEngineError` → ModelLoadError, InferenceError, TrackingError
  - `CalibrationError` → InsufficientPointsError, HomographyError
  - `VideoError` → VideoLoadError, VideoWriteError
  - `ZoneError` → InvalidZoneError, ZoneNotFoundError
  - `LLMError` → APIError, ParseError

### 8. shared/schemas/common.py

| 项目 | 值 |
|---|---|
| 文件名 | shared/schemas/common.py |
| 作用 | 共享 Pydantic Schema |
| 所属层 | shared |
| 依赖模块 | [pydantic] |
| 耦合风险 | 低 |
| 未来扩展 | 添加新 Schema |
| 不能合并原因 | 跨层共享数据结构 |

Schema 设计：
- `ResponseWrapper`：统一 API 响应格式（success, data, error）
- `PaginatedResponse`：分页响应（items, total, page, limit）
- `ErrorDetail`：错误详情（code, message, details）

### 9. docker-compose.yml

| 项目 | 值 |
|---|---|
| 文件名 | docker-compose.yml |
| 作用 | Docker 服务编排 |
| 所属层 | shared |
| 依赖模块 | 无 |
| 耦合风险 | 无 |
| 未来扩展 | 添加新服务 |
| 不能合并原因 | 部署配置独立 |

服务列表：
- `api`：FastAPI 应用（端口 8000）
- `frontend`：React 应用 Nginx（端口 3000）
- `redis`：缓存（端口 6379，可选）

### 10. Makefile

| 项目 | 值 |
|---|---|
| 文件名 | Makefile |
| 作用 | 常用开发命令封装 |
| 所属层 | shared |
| 依赖模块 | 无 |
| 耦合风险 | 无 |
| 未来扩展 | 添加新命令 |
| 不能合并原因 | 开发便利性 |

命令列表：
- `make install`：安装依赖
- `make dev`：启动开发服务器
- `make test`：运行测试
- `make lint`：代码检查
- `make format`：代码格式化
- `make typecheck`：类型检查
- `make docker-up`：Docker 启动
- `make docker-down`：Docker 停止

## 验证清单

- [ ] `python -c "import shared"` 成功
- [ ] `make install` 成功安装所有依赖
- [ ] `make lint` 通过
- [ ] `make format` 通过
- [ ] `make typecheck` 通过
- [ ] `make test` 通过（空测试套件）
- [ ] `docker-compose up` 成功启动
- [ ] `.env.example` 包含所有必要变量

## 工作量评估

```yaml
模块: Phase 0 - 项目初始化
复杂度: 低
预计开发: 0.5-1 天
依赖模块: 无
测试成本: 低（基础设施验证）
风险: 低
未来扩展: 添加新工具、新配置
```

## 技术债检查

```yaml
Phase: 0
当前技术债: 无
耦合情况: 无耦合
扩展风险: 无
是否需要重构: 否
建议拆分方案: 无
```
