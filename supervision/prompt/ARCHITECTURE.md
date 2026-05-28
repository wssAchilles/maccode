# TrafficPerceptionEngine - 系统架构报告

## 1. 项目定位

工业级 AI 交通感知平台。非课设 Demo，而是真实可部署的全栈 AI 系统。

核心能力：
- YOLO 实时目标检测（MPS 硬件加速）
- ByteTrack 多目标跟踪
- LineZone 双向流量计数
- 单应性矩阵速度估算
- WebSocket 实时数据推送
- LLM 智能分析报告
- React 可视化大屏

## 2. 技术栈

| 层 | 技术 | 版本 | 理由 |
|---|---|---|---|
| CV 引擎 | Python + supervision + ultralytics | ≥0.25.0 / ≥8.0.0 | 原生 MPS 支持，130+ API |
| 后端框架 | FastAPI + Uvicorn | ≥0.100.0 | 异步高性能，自动 OpenAPI 文档 |
| 实时通信 | WebSocket (fastapi.websockets) | 内置 | 双向实时推送 |
| 数据库 | SQLite (开发) / PostgreSQL (生产) | - | 轻量→可扩展 |
| 缓存 | Redis (可选) | ≥7.0 | 高频数据缓存 |
| 前端框架 | React + TypeScript | 18.x | 组件化，类型安全 |
| 可视化 | ECharts | ≥5.0 | 丰富图表，适合大屏 |
| LLM 集成 | OpenAI API / 本地模型 | ≥1.0.0 | 交通分析报告生成 |
| 硬件加速 | MPS (Metal Performance Shaders) | M5 芯片 | GPU 推理 3-5x 加速 |
| 容器化 | Docker Compose | - | 一键部署 |
| 代码质量 | Ruff (lint + format) | - | Python 生态最快 |
| 测试 | Pytest | ≥7.0 | 标准测试框架 |

## 3. 系统分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Interface Layer (接口层)                   │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  REST API    │  │  WebSocket   │  │  React Frontend  │  │
│  │  (FastAPI)   │  │  (实时推送)   │  │  (4 页面大屏)    │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                    │            │
├─────────┴─────────────────┴────────────────────┴────────────┤
│                 Application Layer (应用层)                    │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Services    │  │ Orchestrators│  │    Usecases      │  │
│  │  (CV/Stats)  │  │  (流水线调度) │  │  (用例编排)      │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                    │            │
├─────────┴─────────────────┴────────────────────┴────────────┤
│                   Domain Layer (领域层)                       │
│                                                             │
│  ┌────────┐ ┌────────┐ ┌──────┐ ┌───────┐ ┌────────────┐  │
│  │Detection│ │Tracking│ │Zones │ │ Speed │ │ Calibration│  │
│  │(YOLO)  │ │(ByteTrk│ │(Line │ │(估算) │ │  (标定)    │  │
│  │        │ │        │ │Zone) │ │       │ │            │  │
│  └────────┘ └────────┘ └──────┘ └───────┘ └────────────┘  │
│                                                             │
│  纯业务逻辑，零 HTTP/WebSocket/数据库依赖                      │
├─────────────────────────────────────────────────────────────┤
│              Infrastructure Layer (基础设施层)                │
│                                                             │
│  ┌────────┐ ┌────────┐ ┌──────┐ ┌───────┐ ┌────────────┐  │
│  │Database│ │WebSocket│ │Cache │ │Logging│ │    LLM     │  │
│  │(SQLite)│ │Manager │ │(Redis│ │(JSON) │ │(OpenAI/本地)│  │
│  └────────┘ └────────┘ └──────┘ └───────┘ └────────────┘  │
│                                                             │
│  技术实现细节，可替换，不影响领域层                               │
└─────────────────────────────────────────────────────────────┘
```

### 层间依赖规则

```
Interface Layer  ──→  Application Layer  ──→  Domain Layer
       │                     │                     │
       └─────────────────────┴─────────────────────┘
                             │
                    Infrastructure Layer
```

- **Domain Layer**：零外部依赖（只用 numpy, opencv, supervision）
- **Application Layer**：依赖 Domain，编排业务流程
- **Interface Layer**：依赖 Application，处理 HTTP/WS/UI
- **Infrastructure Layer**：被 Application/Interface 使用，可替换实现

禁止：
- Domain 层引用 FastAPI、WebSocket、React
- Interface 层直接调用 Domain 层（必须经过 Application）
- Infrastructure 层包含业务逻辑

## 4. 业务流设计

### 4.1 主数据流

```
视频输入（上传文件 / 摄像头流）
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Pipeline Orchestrator (Application Layer)              │
│  管理任务生命周期：创建→运行→暂停→完成→失败                │
└────────────────────────┬────────────────────────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    ▼                    ▼                    ▼
┌─────────┐      ┌──────────────┐     ┌───────────┐
│ YOLO    │      │ ByteTrack    │     │ LineZone  │
│ 检测    │─────→│ 跟踪         │────→│ 计数      │
│ (MPS)   │      │ (tracker_id) │     │ (in/out)  │
└─────────┘      └──────────────┘     └───────────┘
                         │
                         ▼
                 ┌──────────────┐
                 │ Speed        │ (可选模块)
                 │ Estimator    │
                 │ (单应性变换)  │
                 └──────────────┘
                         │
                         ▼
                 ┌──────────────┐
                 │ FrameReport  │
                 │ (结构化JSON) │
                 └──────┬───────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
   ┌───────────┐ ┌───────────┐ ┌───────────┐
   │ WebSocket │ │ Database  │ │ MJPEG     │
   │ 实时推送  │ │ 持久化    │ │ 视频流    │
   └───────────┘ └───────────┘ └───────────┘
          │             │
          ▼             ▼
   ┌───────────┐ ┌───────────┐
   │ React UI  │ │ LLM       │
   │ 实时更新  │ │ 分析报告  │
   └───────────┘ └───────────┘
```

### 4.2 数据流分类

| 类型 | 数据 | 通道 | 延迟要求 | 存储 |
|---|---|---|---|---|
| **实时流** | FrameReport, 视频帧 | WebSocket, MJPEG | <100ms | 内存 |
| **异步任务** | 视频处理, LLM 报告 | Background Task | 秒级 | 临时文件 |
| **长期存储** | 历史统计, 报告 | Database | 无要求 | SQLite/PG |
| **配置数据** | 区域配置, 标定参数 | REST API | 无要求 | 文件/DB |

### 4.3 核心瓶颈分析

| 环节 | 瓶颈类型 | 解决方案 |
|---|---|---|
| YOLO 推理 | **GPU 计算** | MPS 硬件加速，模型选择 (n/s/m) |
| ByteTrack | CPU 计算 | 轻量，通常不是瓶颈 |
| 视频 I/O | 磁盘/网络 | 异步读取，帧缓冲 |
| WebSocket | 网络 | 帧采样推送（非每帧） |
| LLM API | 网络延迟 | 异步调用，缓存报告 |

## 5. 模块依赖关系

```
                    ┌─────────────────┐
                    │   supervision   │
                    │   (外部库)      │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
  ┌───────────┐      ┌──────────────┐     ┌───────────┐
  │ sv.Detect.│      │ sv.ByteTrack │     │ sv.Line   │
  │ from_ultr.│      │ update_with_ │     │ Zone      │
  │           │      │ detections   │     │ trigger   │
  └─────┬─────┘      └──────┬───────┘     └─────┬─────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                   ┌─────────────────┐
                   │ domain/         │
                   │ detection/      │
                   │ tracking/       │
                   │ zones/          │
                   └────────┬────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
     ┌──────────────┐ ┌──────────┐ ┌──────────┐
     │ domain/speed/│ │ domain/  │ │ domain/  │
     │ (可选)       │ │ reports/ │ │ calib/   │
     └──────────────┘ └──────────┘ └──────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ application/    │
                   │ services/       │
                   │ orchestrators/  │
                   └────────┬────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
     ┌──────────────┐ ┌──────────┐ ┌──────────┐
     │ interfaces/  │ │ infra/   │ │ shared/  │
     │ api/ frontend│ │ db/ws/llm│ │ configs/ │
     └──────────────┘ └──────────┘ └──────────┘
```

## 6. 关键 supervision API 映射

| 功能 | supervision API | 源文件 | 返回值 |
|---|---|---|---|
| 检测结果转换 | `sv.Detections.from_ultralytics()` | `detection/core.py` | `Detections` |
| 多目标跟踪 | `sv.ByteTrack().update_with_detections()` | `tracker/byte_tracker/core.py` | `Detections` + tracker_id |
| 双向计数 | `sv.LineZone().trigger()` | `detection/line_zone.py` | `(in_bool, out_bool)` |
| 区域检测 | `sv.PolygonZone().trigger()` | `detection/tools/polygon_zone.py` | `NDArray[bool]` |
| 边界框标注 | `sv.BoxAnnotator().annotate()` | `annotators/core.py` | `np.ndarray` |
| 标签标注 | `sv.LabelAnnotator().annotate()` | `annotators/core.py` | `np.ndarray` |
| 轨迹标注 | `sv.TraceAnnotator().annotate()` | `annotators/core.py` | `np.ndarray` |
| 线标注 | `sv.LineZoneAnnotator().annotate()` | `detection/line_zone.py` | `np.ndarray` |
| 视频信息 | `sv.VideoInfo.from_video_path()` | `utils/video.py` | `VideoInfo` |
| 视频写入 | `sv.VideoSink()` | `utils/video.py` | `VideoSink` |
| 帧生成器 | `sv.get_video_frames_generator()` | `utils/video.py` | `Generator` |
| 几何点 | `sv.Point(x, y)` | `geometry/core.py` | `Point` |

## 7. 硬件加速策略

### MPS (Metal Performance Shaders) - M5 芯片

验证 MPS 可用：`torch.backends.mps.is_available()` → True

YOLO 使用 MPS：`model.to("mps")` 或推理时 `model(frame, device="mps")`

### 性能预期

| 设备 | YOLOv11n 推理时间 | 相对速度 |
|---|---|---|
| CPU (M5) | ~15ms | 1x |
| MPS (M5) | ~4ms | 3.7x |
| CUDA (RTX 3060) | ~3ms | 5x |

### 模型选择策略

| 模型 | 参数量 | MPS 推理 | 适用场景 |
|---|---|---|---|
| YOLOv11n | 2.6M | ~4ms | 实时流，边缘设备 |
| YOLOv11s | 9.4M | ~8ms | 平衡速度/精度 |
| YOLOv11m | 20.1M | ~15ms | 高精度需求 |

推荐：开发用 `yolo11n`，演示用 `yolo11s`。

## 8. 速度估算数学模型

### 单应性变换原理

```
像素坐标系 (u, v)          真实世界坐标系 (X, Y)
    ┌───────────┐              ┌───────────┐
    │           │              │           │
    │  透视畸变  │   H 矩阵    │  真实距离  │
    │           │ ──────────→  │           │
    │  (像素)   │              │   (米)    │
    └───────────┘              └───────────┘

H = cv2.findHomography(pixel_pts, world_pts)
[X, Y] = cv2.perspectiveTransform([u, v], H)
```

### 速度计算公式

```
速度 = 位移 / 时间

位移 = √((X₂-X₁)² + (Y₂-Y₁)²)   # 世界坐标系，单位：米
时间 = (frame₂ - frame₁) / fps     # 单位：秒
速度_m/s = 位移 / 时间
速度_kmh = 速度_m/s × 3.6
```

### 标定流程

1. 在视频帧上选取 4+ 个参考点（像素坐标）
2. 测量这些点在真实世界中的坐标（米）
3. `cv2.findHomography(pixel_pts, world_pts)` → H 矩阵
4. 每帧目标像素坐标 → `perspectiveTransform` → 世界坐标
5. 计算同一 tracker_id 相邻帧的位移
6. 位移 / 时间间隔 = 速度

### 防抖动处理

| 策略 | 方法 | 参数 |
|---|---|---|
| 滑动窗口 | 取最近 N 帧速度中位数 | N=5 |
| 最小位移 | 静止目标不计算 | 阈值=0.1m |
| 异常过滤 | 速度 > 200 km/h 视为异常 | 上限=200 |
| 平滑滤波 | 指数移动平均 | α=0.3 |

## 9. 数据模型

### FrameReport (实时帧报告)

| 字段 | 类型 | 说明 |
|---|---|---|
| frame_index | int | 帧序号 |
| timestamp_sec | float | 时间戳（秒） |
| fps | float | 当前帧率 |
| active_tracks | list | 活跃轨迹列表 |
| active_tracks[].tracker_id | int | 跟踪 ID |
| active_tracks[].class_id | int | 类别 ID |
| active_tracks[].class_name | str | 类别名称 |
| active_tracks[].confidence | float | 置信度 |
| active_tracks[].xyxy | list | 边界框 [x1,y1,x2,y2] |
| active_tracks[].speed_kmh | float\|null | 速度（可选） |
| zone_stats | list | 区域统计 |
| zone_stats[].name | str | 区域名称 |
| zone_stats[].in_count | int | 进入计数 |
| zone_stats[].out_count | int | 离开计数 |
| total_in | int | 总进入 |
| total_out | int | 总离开 |

### CumulativeStats (累计统计)

| 字段 | 类型 | 说明 |
|---|---|---|
| total_frames | int | 总帧数 |
| total_unique_tracks | int | 唯一目标数 |
| zone_stats | list | 各区域统计 |
| avg_fps | float | 平均帧率 |
| avg_speed_kmh | float\|null | 平均速度 |
| processing_time_sec | float | 总处理时间 |

### ZoneConfig (区域配置)

| 字段 | 类型 | 说明 |
|---|---|---|
| name | str | 区域名称 |
| line_start | [x, y] | 线起点 |
| line_end | [x, y] | 线终点 |

### CalibrationConfig (标定配置)

| 字段 | 类型 | 说明 |
|---|---|---|
| pixel_points | list | 像素坐标 [[u1,v1], ...] |
| world_points | list | 世界坐标 [[X1,Y1], ...]（米） |

## 10. API 设计

### REST API

| 端点 | 方法 | 功能 | 请求体 | 响应 |
|---|---|---|---|---|
| `/api/video/upload` | POST | 上传视频 | multipart/form-data | `{task_id, path}` |
| `/api/video/process` | POST | 启动处理 | `{source, config, zones}` | `{task_id}` |
| `/api/video/stream/{id}` | GET | MJPEG 流 | - | video/mp4 stream |
| `/api/video/stop/{id}` | POST | 停止处理 | - | `{status}` |
| `/api/stats/realtime` | GET | 实时统计 | - | `FrameReport` |
| `/api/stats/history` | GET | 历史统计 | `?limit=100` | `[FrameReport]` |
| `/api/stats/cumulative` | GET | 累计统计 | - | `CumulativeStats` |
| `/api/zones` | GET | 获取区域 | - | `[ZoneConfig]` |
| `/api/zones` | PUT | 更新区域 | `[ZoneConfig]` | `{status}` |
| `/api/calibration` | GET | 获取标定 | - | `CalibrationConfig` |
| `/api/calibration` | PUT | 更新标定 | `CalibrationConfig` | `{status}` |
| `/api/ai/report` | POST | 生成报告 | `{stats, history}` | `{report}` |

### WebSocket

| 端点 | 方向 | 消息类型 | 数据 |
|---|---|---|---|
| `/ws/stream` | Server→Client | `frame_report` | FrameReport JSON |
| `/ws/stream` | Server→Client | `video_frame` | base64 编码帧 |
| `/ws/stream` | Server→Client | `status` | 处理状态 |
| `/ws/stream` | Client→Server | `command` | 控制指令 |

## 11. 前端页面设计

### 页面 1: 实时监控大屏 (RealtimeMonitor)

布局：
- 左侧：视频播放器（MJPEG 流）
- 右侧：实时数据卡片（总进入/离开/FPS/活跃目标/平均速度）
- 底部：实时流量趋势图（ECharts 折线图，最近 60 秒）

### 页面 2: 历史数据分析 (HistoricalAnalysis)

- 时间范围选择器
- 流量趋势图（ECharts 折线图）
- 速度分布图（ECharts 直方图）
- 热力图（目标密度）
- 数据导出（CSV/JSON）

### 页面 3: 区域配置管理 (ZoneConfig)

- 视频帧上可视化编辑区域
- 拖拽调整线段位置
- 添加/删除区域
- 标定点设置（速度估算）
- 配置保存/加载

### 页面 4: AI 分析报告 (AIReport)

- 一键生成报告按钮
- 报告内容展示（Markdown 渲染）
- 历史报告列表
- 报告导出（PDF）

## 12. 部署架构

```
┌─────────────────────────────────────────┐
│           Docker Compose                │
│                                         │
│  ┌──────────────┐  ┌──────────────────┐│
│  │  API Server  │  │  Frontend (Nginx)││
│  │  (FastAPI)   │  │  (React Build)  ││
│  │  Port: 8000  │  │  Port: 3000     ││
│  └──────┬───────┘  └────────┬─────────┘│
│         │                   │          │
│  ┌──────┴───────┐  ┌───────┴──────────┐│
│  │  SQLite/PG   │  │  Redis (可选)    ││
│  │  Port: 5432  │  │  Port: 6379     ││
│  └──────────────┘  └──────────────────┘│
└─────────────────────────────────────────┘
```

## 13. 工作量评估

| Phase | 模块 | 复杂度 | 时间 | 风险 |
|---|---|---|---|---|
| Phase 0 | 项目初始化 | 低 | 0.5-1 天 | 低 |
| Phase 1 | CV 核心引擎 | 中 | 2-3 天 | 中 |
| Phase 2 | 速度估算 | **高** | 2-4 天 | **高** |
| Phase 3 | FastAPI 后端 | 中 | 2-3 天 | 中 |
| Phase 4 | React 前端 | 中 | 3-4 天 | 低 |
| **总计** | | | **12-15 天** | |

### Phase 2 风险详解

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| 透视标定误差 | 速度不准 | 多点标定，误差分析 |
| Tracker ID 抖动 | 速度跳变 | 滑动窗口平滑 |
| FPS 不稳定 | 时间计算误差 | 使用实际时间戳 |
| 静止目标干扰 | 速度异常 | 最小位移阈值 |

## 14. 质量保障

### 测试策略

| 类型 | 覆盖范围 | 工具 |
|---|---|---|
| 单元测试 | Domain 层每个模块 | Pytest |
| 集成测试 | Application 层服务 | Pytest + httpx |
| E2E 测试 | API + WebSocket | Playwright |
| 性能测试 | 推理速度 | benchmark.py |

### 代码质量

- Lint + Format: Ruff
- 类型检查: mypy
- 测试覆盖率: ≥ 80%
- Pre-commit hooks: 自动检查
