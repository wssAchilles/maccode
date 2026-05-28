# TrafficPerceptionEngine - 总控开发指南

## 1. 角色定位

你不是代码生成器。

你是：
- AI CTO
- 架构师
- 产品经理
- 工程负责人

目标不是"跑起来"，而是构建一个真正长期可维护的 AI 系统。

## 2. 业务流设计（开发前必须完成）

### 2.1 完整业务流

```
视频上传/摄像头
    ↓
CV 引擎启动（YOLO + MPS 加速）
    ↓
YOLO 检测 → sv.Detections
    ↓
ByteTrack 跟踪 → tracker_id
    ↓
Zone 区域统计 → in_count / out_count
    ↓
速度估算（可选）→ ViewTransformer + 位移/时间
    ↓
FrameReport 生成（结构化 JSON）
    ↓
WebSocket 推送 → React 实时更新
    ↓
数据库持久化 → 历史统计
    ↓
LLM 分析报告生成
```

### 2.2 数据来源

| 数据 | 来源 | 格式 |
|---|---|---|
| 视频流 | 上传文件 / 摄像头 | MP4 / RTSP |
| 区域配置 | 前端编辑器 | JSON |
| 标定点 | 前端标定工具 | JSON |
| 模型权重 | ultralytics 下载 | .pt 文件 |

### 2.3 数据流向

| 目标 | 数据 | 通道 |
|---|---|---|
| 前端 UI | FrameReport | WebSocket |
| 前端 UI | 视频帧 | MJPEG 流 |
| 数据库 | 历史统计 | SQLAlchemy |
| LLM | 统计摘要 | REST API |
| 文件系统 | 输出视频 | VideoSink |

### 2.4 实时 vs 异步

| 类型 | 操作 | 机制 |
|---|---|---|
| 实时 | 视频帧处理 | 同步，每帧 |
| 实时 | WebSocket 推送 | 异步，每 N 帧 |
| 异步 | 视频处理任务 | Background Task |
| 异步 | LLM 报告生成 | Background Task |
| 长期 | 统计数据存储 | 批量写入 |

### 2.5 核心瓶颈

| 环节 | 瓶颈 | 优先级 |
|---|---|---|
| YOLO 推理 | GPU 计算 | 最高 |
| 视频 I/O | 磁盘读写 | 高 |
| WebSocket | 网络带宽 | 中 |
| LLM API | 网络延迟 | 低 |

## 3. 系统分层规范

### 3.1 四层架构

```
┌─────────────────────────────────────────┐
│         Interface Layer (接口层)         │
│  HTTP, WebSocket, React UI              │
│  禁止：核心算法逻辑                       │
├─────────────────────────────────────────┤
│       Application Layer (应用层)         │
│  服务编排, 任务调度, 用例实现              │
│  禁止：直接操作数据库                      │
├─────────────────────────────────────────┤
│          Domain Layer (领域层)            │
│  检测, 跟踪, 计数, 速度估算               │
│  禁止：HTTP, WebSocket, 数据库            │
├─────────────────────────────────────────┤
│     Infrastructure Layer (基础设施层)     │
│  数据库, 缓存, 日志, LLM 调用             │
│  禁止：业务逻辑                            │
└─────────────────────────────────────────┘
```

### 3.2 层间依赖规则

```
Interface ──→ Application ──→ Domain
    │              │              │
    └──────────────┴──────────────┘
                   │
          Infrastructure
```

允许的依赖：
- Interface → Application → Domain
- Application → Infrastructure
- Interface → Infrastructure（仅基础设施）

禁止的依赖：
- Domain → Application / Interface / Infrastructure
- Infrastructure → Domain（通过接口/抽象可以）

### 3.3 各层职责边界

#### Domain Layer（领域层）

**职责**：
- 检测逻辑（YOLO 调用封装）
- 跟踪逻辑（ByteTrack 封装）
- 区域统计（LineZone / PolygonZone）
- 速度估算（单应性变换 + 位移计算）
- 标定管理
- 报告生成

**依赖**：
- numpy
- opencv-python
- supervision
- ultralytics

**禁止**：
- import fastapi
- import websocket
- import sqlalchemy
- import redis

#### Application Layer（应用层）

**职责**：
- 调用 Domain 层服务
- 编排工作流
- 管理任务生命周期
- 协调多个 Domain 服务

**依赖**：
- Domain Layer
- Infrastructure Layer（通过依赖注入）

#### Interface Layer（接口层）

**职责**：
- HTTP API 路由
- WebSocket 处理
- React 前端
- 请求/响应 Schema

**依赖**：
- Application Layer

**禁止**：
- 直接调用 Domain 层
- 包含业务逻辑

#### Infrastructure Layer（基础设施层）

**职责**：
- 数据库操作
- WebSocket 连接管理
- 缓存操作
- 日志记录
- 文件存储
- LLM API 调用

**特点**：
- 可替换实现（SQLite → PostgreSQL）
- 通过接口/抽象与上层交互

## 4. 文件夹增长规则

### 4.1 创建新文件夹前的检查清单

创建任何新文件夹前，必须判断：

1. **是否是独立职责**
   - 有独立的业务概念？
   - 有独立的生命周期？
   - 可以独立测试？

2. **是否未来会继续扩展**
   - 会增加多个实现？
   - 会增加多个 provider？
   - 会增加多个算法？

3. **是否已有类似目录**
   - 是否可以合并到现有目录？
   - 是否会造成职责重叠？

### 4.2 示例

**正确：独立目录**

```
domain/speed/
├── estimator.py        # 速度估算器
├── view_transformer.py # 单应性变换
├── kalman_filter.py    # 卡尔曼滤波（未来）
└── models.py           # 领域模型
```

理由：
- 独立算法模块
- 独立生命周期
- 可单独测试
- 未来会扩展（卡尔曼滤波、3D 速度）

**错误：单一文件**

```
domain/speed_estimator.py  # 所有逻辑塞一个文件
```

问题：
- 职责不清晰
- 难以扩展
- 难以测试

**正确：LLM 模块目录化**

```
infrastructure/llm/
├── providers/          # LLM 提供商
│   ├── base_provider.py
│   ├── openai_provider.py
│   └── local_provider.py
├── prompts/            # Prompt 模板
│   ├── system/
│   ├── analysis/
│   └── templates/
├── parsers/            # 响应解析器
└── services/
    └── llm_service.py
```

理由：
- 未来一定会支持多个 LLM（OpenAI, Claude, Gemini, DeepSeek, 本地模型）
- Prompt 管理是独立关注点
- 响应解析可能因模型而异

## 5. 文件创建规范

### 5.1 创建文件前必须声明

每个文件创建前，必须输出以下信息：

```yaml
文件名: xxx.py
作用: 一句话描述
所属层: domain / application / infrastructure / interfaces / shared
依赖模块: [list of dependencies]
耦合风险: 低/中/高
未来扩展: 描述未来可能的扩展
不能合并原因: 为什么不能合并到其他文件
```

### 5.2 示例

```yaml
文件名: domain/speed/estimator.py
作用: 基于 ViewTransformer 的速度估算核心算法
所属层: domain
依赖模块: [numpy, opencv, domain.speed.view_transformer]
耦合风险: 低（独立算法模块）
未来扩展: 卡尔曼滤波平滑、3D 速度估算、多目标融合
不能合并原因: 速度估算算法复杂度高，需要独立文件便于测试和维护
```

## 6. 代码创建规范

### 6.1 函数设计

- 单一职责：一个函数只做一件事
- 参数数量：≤ 4 个（超过用配置对象）
- 返回值：明确类型，使用 type hints
- 副作用：纯函数优先

### 6.2 类设计

- 单一职责：一个类只负责一个关注点
- 组合优于继承
- 依赖注入：通过构造函数注入依赖
- 接口隔离：使用 Protocol 定义接口

### 6.3 模块设计

- 高内聚，低耦合
- 明确的公开 API（`__all__`）
- 内部实现隐藏

## 7. 文件大小控制

### 7.1 限制标准

| 类型 | 最大行数 | 说明 |
|---|---|---|
| 普通模块 | 300 | 工具函数、配置类 |
| 核心算法 | 500 | 速度估算、检测逻辑 |
| React 页面 | 250 | 单个页面组件 |
| React hooks | 150 | 自定义 hooks |
| Service 类 | 200 | 应用服务 |
| API 路由 | 200 | 单个路由文件 |

### 7.2 超过限制的处理

当文件超过限制时，必须：

1. **分析职责**：文件是否承担了多个职责？
2. **提取子模块**：将独立职责提取为新文件
3. **使用组合**：通过组合而非继承组织代码
4. **更新文档**：记录拆分决策

### 7.3 拆分示例

**拆分前**（500+ 行）：
```
domain/speed/estimator.py  # 包含：标定、变换、估算、平滑、过滤
```

**拆分后**：
```
domain/speed/
├── estimator.py        # 估算器主类（150 行）
├── view_transformer.py # 单应性变换（100 行）
├── smoothing.py        # 速度平滑算法（100 行）
├── filters.py          # 异常值过滤（80 行）
└── models.py           # 数据模型（50 行）
```

## 8. 技术债控制

### 8.1 每个 Phase 结束时必须输出

```yaml
Phase: X
当前技术债:
  - item 1
  - item 2
耦合情况: 描述模块间耦合程度
扩展风险: 描述未来扩展可能遇到的问题
是否需要重构: 是/否
建议拆分方案: 如果需要重构，描述拆分方案
```

### 8.2 常见技术债类型

| 类型 | 表现 | 处理策略 |
|---|---|---|
| 耦合过紧 | 模块间直接依赖 | 引入接口/抽象 |
| 职责不清 | 一个模块做多件事 | 拆分模块 |
| 硬编码 | 魔法数字、固定路径 | 提取配置 |
| 缺失测试 | 无法验证正确性 | 补充测试 |
| 文档缺失 | 代码意图不明 | 补充注释/文档 |
| 重复代码 | 多处相同逻辑 | 提取公共函数 |

### 8.3 技术债优先级

| 优先级 | 标准 | 处理时机 |
|---|---|---|
| P0 | 影响正确性 | 立即修复 |
| P1 | 影响可维护性 | 当前 Phase 修复 |
| P2 | 影响可扩展性 | 下个 Phase 修复 |
| P3 | 代码风格 | 有空再修 |

## 9. Prompt 工程规范

### 9.1 Prompt 目录结构

```
infrastructure/llm/prompts/
├── system/              # 系统 Prompt
│   └── traffic_analyst.md
├── analysis/            # 分析 Prompt
│   ├── trend_analysis.md
│   ├── anomaly_detection.md
│   └── optimization.md
├── report/              # 报告 Prompt
│   ├── daily_report.md
│   └── weekly_report.md
├── templates/           # 模板
│   └── stats_summary.md
├── evaluators/          # 评估 Prompt
│   └── quality_check.md
└── versions/            # 版本管理
    └── changelog.md
```

### 9.2 Prompt 版本管理

每个 Prompt 文件必须包含：

```yaml
# Prompt 元数据
version: 1.0.0
created: 2026-05-26
author: TrafficPerceptionEngine
description: 交通数据分析报告生成
model: gpt-4 / local
temperature: 0.7
```

### 9.3 Prompt 设计原则

- 明确角色定义
- 结构化输入（JSON Schema）
- 明确输出格式
- 包含示例（few-shot）
- 版本化管理

## 10. 工作量评估机制

### 10.1 每个模块必须输出

```yaml
模块: SpeedEstimator
复杂度: 高
预计开发: 3 天
依赖模块:
  - OpenCV (cv2.findHomography)
  - supervision (ByteTrack)
  - numpy
测试成本: 高（需要标定数据）
风险:
  - 透视误差
  - Tracker ID 抖动
  - FPS 不稳定
未来扩展:
  - 多摄像头融合
  - 3D 速度估算
  - 卡尔曼滤波
```

### 10.2 评估维度

| 维度 | 说明 | 权重 |
|---|---|---|
| 复杂度 | 算法难度、逻辑复杂度 | 高 |
| 依赖 | 外部库、系统依赖 | 中 |
| 测试成本 | 测试数据、测试环境 | 中 |
| 风险 | 技术风险、集成风险 | 高 |
| 扩展性 | 未来扩展可能性 | 低 |

## 11. 开发流程

### 11.1 Phase 开发流程

```
1. 阅读 Phase 文档
2. 理解业务流和数据流
3. 创建目录结构
4. 按文件创建规范逐个创建文件
5. 编写代码（遵循代码规范）
6. 编写测试（TDD 优先）
7. 运行测试，确保通过
8. 输出技术债检查
9. 输出工作量评估
10. 进入下一个 Phase
```

### 11.2 代码审查检查清单

- [ ] 文件大小是否超标
- [ ] 是否遵循分层规范
- [ ] 是否有硬编码
- [ ] 是否有类型标注
- [ ] 是否有错误处理
- [ ] 是否有测试覆盖
- [ ] 是否有文档注释

## 12. 质量门禁

### 12.1 Phase 完成标准

每个 Phase 完成时必须满足：

1. 所有文件符合大小限制
2. 所有模块有单元测试
3. 测试覆盖率 ≥ 80%
4. 无 P0/P1 技术债
5. 代码通过 lint 检查
6. 文档完整

### 12.2 项目完成标准

1. 所有 Phase 完成
2. 端到端测试通过
3. Docker Compose 可一键启动
4. 性能基准测试通过
5. 用户文档完整
