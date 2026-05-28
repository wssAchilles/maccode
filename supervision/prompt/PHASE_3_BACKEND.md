# Phase 3: FastAPI 后端

## 目标

实现应用层服务编排、REST API、WebSocket 实时推送、LLM 集成。

复杂度：中 | 风险：中 | 预计时间：2-3 天

## 业务流

```
前端请求
    ↓
Interface Layer (FastAPI 路由)
    ↓
Application Layer (服务编排)
    ↓
Domain Layer (CV 引擎)
    ↓
FrameReport
    ↓
Infrastructure Layer
    ├── WebSocket Manager → 实时推送
    ├── Database Repository → 持久化
    └── LLM Service → 分析报告
```

## 目录结构

```
application/
├── services/
│   ├── cv_service.py           # CV 引擎服务
│   ├── video_service.py        # 视频处理服务
│   └── stats_service.py        # 统计服务
├── orchestrators/
│   └── pipeline_orchestrator.py # 流水线编排器
└── usecases/
    ├── process_video.py        # 处理视频用例
    └── generate_report.py      # 生成报告用例

infrastructure/
├── database/
│   ├── models.py               # SQLAlchemy 模型
│   ├── repository.py           # 数据仓库
│   └── engine.py               # 数据库引擎
├── websocket/
│   ├── manager.py              # 连接管理器
│   └── handlers.py             # 消息处理器
├── logging/
│   └── logger.py               # 结构化日志
└── llm/
    ├── providers/
    │   ├── base_provider.py    # LLM 提供商接口
    │   └── openai_provider.py  # OpenAI 实现
    ├── prompts/
    │   ├── system/
    │   └── analysis/
    ├── parsers/
    │   └── report_parser.py
    └── services/
        └── llm_service.py      # LLM 服务

interfaces/
├── api/
│   ├── app.py                  # FastAPI 应用工厂
│   ├── dependencies.py         # 依赖注入
│   ├── schemas/                # Pydantic Schema
│   └── routes/                 # API 路由
└── websocket/
    └── routes.py               # WebSocket 路由
```

## 文件清单

### Application Layer

#### 1. application/services/cv_service.py

| 项目 | 值 |
|---|---|
| 作用 | CV 引擎服务：初始化、运行、停止 |
| 所属层 | application |
| 依赖模块 | domain.detection, domain.tracking, domain.zones, domain.reports |
| 耦合风险 | 中 |
| 未来扩展 | 多引擎切换 |

公开 API：
- `CVService(config)` — 初始化
- `initialize()` — 初始化引擎
- `process_frame(frame) -> FrameReport | None` — 单帧处理
- `get_cumulative_stats() -> CumulativeStats` — 累计统计
- `reset()` — 重置状态

#### 2. application/services/video_service.py

| 项目 | 值 |
|---|---|
| 作用 | 视频处理服务：文件管理、帧读取 |
| 所属层 | application |
| 依赖模块 | opencv, supervision |
| 耦合风险 | 低 |
| 未来扩展 | 摄像头流、RTSP |

公开 API：
- `VideoService()` — 初始化
- `load_video(path) -> VideoInfo` — 加载视频
- `get_frames_generator(path) -> Generator` — 帧生成器
- `create_sink(path, video_info) -> VideoSink` — 创建写入器

#### 3. application/services/stats_service.py

| 项目 | 值 |
|---|---|
| 作用 | 统计服务：历史数据查询 |
| 所属层 | application |
| 依赖模块 | infrastructure.database |
| 耦合风险 | 低 |
| 未来扩展 | 缓存、聚合统计 |

核心职责：存储统计数据、查询历史、生成趋势

#### 4. application/orchestrators/pipeline_orchestrator.py

| 项目 | 值 |
|---|---|
| 作用 | 流水线编排器：任务生命周期管理 |
| 所属层 | application |
| 依赖模块 | application.services |
| 耦合风险 | 中 |
| 未来扩展 | 任务队列、并发控制 |

公开 API：
- `PipelineOrchestrator(cv_service, video_service, stats_service)`
- `start_task(source, config) -> str` — 启动任务，返回 task_id
- `stop_task(task_id)` — 停止任务
- `get_task_status(task_id) -> TaskStatus` — 查询状态
- `get_task_result(task_id) -> TaskResult` — 获取结果

#### 5. application/usecases/process_video.py

| 项目 | 值 |
|---|---|
| 作用 | 处理视频用例 |
| 所属层 | application |
| 依赖模块 | application.orchestrators |
| 耦合风险 | 低 |
| 未来扩展 | 批量处理 |

核心职责：编排视频处理流程

#### 6. application/usecases/generate_report.py

| 项目 | 值 |
|---|---|
| 作用 | 生成报告用例 |
| 所属层 | application |
| 依赖模块 | infrastructure.llm, application.services |
| 耦合风险 | 低 |
| 未来扩展 | 多种报告类型 |

核心职责：收集统计数据、调用 LLM、格式化报告

### Infrastructure Layer

#### 7. infrastructure/database/models.py

| 项目 | 值 |
|---|---|
| 作用 | SQLAlchemy 数据库模型 |
| 所属层 | infrastructure |
| 依赖模块 | sqlalchemy |
| 耦合风险 | 低 |
| 未来扩展 | 添加新表 |

表设计：
- `FrameReportModel` — 帧报告存储
- `CumulativeStatsModel` — 累计统计存储
- `ZoneConfigModel` — 区域配置存储
- `CalibrationConfigModel` — 标定配置存储
- `AIReportModel` — AI 报告存储

#### 8. infrastructure/database/repository.py

| 项目 | 值 |
|---|---|
| 作用 | 数据仓库：CRUD 操作 |
| 所属层 | infrastructure |
| 依赖模块 | sqlalchemy, infrastructure.database.models |
| 耦合风险 | 低 |
| 未来扩展 | 缓存层 |

公开 API：
- `FrameReportRepository(session)`
- `save(report)` — 保存
- `get_latest(limit) -> list` — 查询最近
- `get_by_time_range(start, end) -> list` — 按时间查询

#### 9. infrastructure/database/engine.py

| 项目 | 值 |
|---|---|
| 作用 | 数据库引擎：连接管理 |
| 所属层 | infrastructure |
| 依赖模块 | sqlalchemy |
| 耦合风险 | 低 |
| 未来扩展 | 连接池、读写分离 |

核心职责：创建引擎、会话管理、表创建

#### 10. infrastructure/websocket/manager.py

| 项目 | 值 |
|---|---|
| 作用 | WebSocket 连接管理器 |
| 所属层 | infrastructure |
| 依赖模块 | fastapi.websockets |
| 耦合风险 | 低 |
| 未来扩展 | Redis Pub/Sub |

公开 API：
- `WebSocketManager()`
- `connect(websocket)` — 连接
- `disconnect(websocket)` — 断开
- `broadcast(message)` — 广播
- `get_connection_count() -> int` — 连接数

#### 11. infrastructure/llm/providers/base_provider.py

| 项目 | 值 |
|---|---|
| 作用 | LLM 提供商抽象接口 |
| 所属层 | infrastructure |
| 依赖模块 | abc |
| 耦合风险 | 低 |
| 未来扩展 | 多提供商实现 |

接口：`generate(prompt, temperature, max_tokens) -> str`, `get_model_name() -> str`

#### 12. infrastructure/llm/providers/openai_provider.py

| 项目 | 值 |
|---|---|
| 作用 | OpenAI API 实现 |
| 所属层 | infrastructure |
| 依赖模块 | openai |
| 耦合风险 | 低 |
| 未来扩展 | 其他提供商 |

核心职责：调用 OpenAI API、错误处理、重试逻辑

#### 13. infrastructure/llm/services/llm_service.py

| 项目 | 值 |
|---|---|
| 作用 | LLM 服务：报告生成 |
| 所属层 | infrastructure |
| 依赖模块 | providers, parsers |
| 耦合风险 | 低 |
| 未来扩展 | 多种报告类型 |

公开 API：
- `LLMService(provider)`
- `generate_traffic_report(stats, history) -> str`
- `generate_trend_analysis(stats) -> str`

### Interface Layer

#### 14. interfaces/api/app.py

| 项目 | 值 |
|---|---|
| 作用 | FastAPI 应用工厂 |
| 所属层 | interfaces |
| 依赖模块 | fastapi |
| 耦合风险 | 低 |

核心职责：创建应用、注册路由、配置中间件

#### 15. interfaces/api/dependencies.py

| 项目 | 值 |
|---|---|
| 作用 | 依赖注入 |
| 所属层 | interfaces |
| 依赖模块 | application.services |
| 耦合风险 | 低 |

核心职责：提供服务实例、数据库会话

#### 16. interfaces/api/routes/video.py

| 项目 | 值 |
|---|---|
| 作用 | 视频 API 路由 |
| 所属层 | interfaces |
| 依赖模块 | application.orchestrators |
| 耦合风险 | 低 |

端点：
- `POST /api/video/upload` — 上传视频
- `POST /api/video/process` — 启动处理
- `GET /api/video/stream/{id}` — MJPEG 流
- `POST /api/video/stop/{id}` — 停止处理

#### 17. interfaces/api/routes/stats.py

| 项目 | 值 |
|---|---|
| 作用 | 统计 API 路由 |
| 所属层 | interfaces |
| 依赖模块 | application.services |
| 耦合风险 | 低 |

端点：
- `GET /api/stats/realtime` — 实时统计
- `GET /api/stats/history` — 历史统计
- `GET /api/stats/cumulative` — 累计统计

#### 18. interfaces/api/routes/zones.py

| 项目 | 值 |
|---|---|
| 作用 | 区域 API 路由 |
| 所属层 | interfaces |
| 依赖模块 | application.services |
| 耦合风险 | 低 |

端点：
- `GET /api/zones` — 获取区域
- `PUT /api/zones` — 更新区域

#### 19. interfaces/api/routes/ai_report.py

| 项目 | 值 |
|---|---|
| 作用 | AI 报告 API 路由 |
| 所属层 | interfaces |
| 依赖模块 | application.usecases |
| 耦合风险 | 低 |

端点：
- `POST /api/ai/report` — 生成报告

#### 20. interfaces/websocket/routes.py

| 项目 | 值 |
|---|---|
| 作用 | WebSocket 路由 |
| 所属层 | interfaces |
| 依赖模块 | infrastructure.websocket |
| 耦合风险 | 低 |

端点：
- `WS /ws/stream` — 实时推送

## 测试计划

### 单元测试

- test_cv_service.py (~6 tests)
- test_video_service.py (~4 tests)
- test_stats_service.py (~4 tests)
- test_pipeline_orchestrator.py (~6 tests)
- test_websocket_manager.py (~4 tests)
- test_llm_service.py (~4 tests)

### 集成测试

- test_api_video.py (~6 tests)
- test_api_stats.py (~4 tests)
- test_api_zones.py (~4 tests)
- test_api_ai_report.py (~3 tests)
- test_websocket.py (~3 tests)

## 验证清单

- [ ] FastAPI 应用启动成功
- [ ] OpenAPI 文档自动生成
- [ ] 视频上传端点正常
- [ ] 视频处理任务启动正常
- [ ] MJPEG 流正常播放
- [ ] 统计 API 返回正确数据
- [ ] 区域 CRUD 正常
- [ ] WebSocket 连接成功
- [ ] WebSocket 推送 FrameReport
- [ ] LLM 报告生成正常
- [ ] 所有单元测试通过
- [ ] 集成测试通过

## 工作量评估

```yaml
模块: Phase 3 - FastAPI 后端
复杂度: 中
预计开发: 2-3 天
依赖模块:
  - FastAPI
  - SQLAlchemy
  - WebSocket
  - OpenAI API
测试成本: 中
风险: 中（WebSocket 连接管理）
未来扩展:
  - 任务队列
  - 缓存层
  - 微服务拆分
```

## 技术债检查

```yaml
Phase: 3
当前技术债: 无
耦合情况: Application 层依赖 Domain + Infrastructure
扩展风险: 低
是否需要重构: 否
建议拆分方案: 无
```
