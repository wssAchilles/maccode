# Phase 1: CV 核心引擎

## 目标

实现 CV 领域层：检测、跟踪、区域统计。验证 MPS 推理链路。

复杂度：中 | 风险：中 | 预计时间：2-3 天

## 业务流

```
视频帧输入
    ↓
YOLO 检测（MPS 加速）→ sv.Detections
    ↓
类别过滤（可选）→ 目标类别筛选
    ↓
ByteTrack 跟踪 → sv.Detections + tracker_id
    ↓
LineZone 触发 → in_count / out_count
    ↓
标注渲染 → Box + Label + Trace + Line
    ↓
FrameReport 生成 → 结构化 JSON
```

## 目录结构

```
domain/
├── __init__.py
├── detection/
│   ├── __init__.py
│   ├── models.py               # Detection 领域模型
│   └── service.py              # 检测服务（YOLO 封装）
├── tracking/
│   ├── __init__.py
│   ├── models.py               # Track 领域模型
│   └── service.py              # 跟踪服务（ByteTrack 封装）
├── zones/
│   ├── __init__.py
│   ├── models.py               # Zone 领域模型
│   └── service.py              # 区域统计服务（LineZone 封装）
└── reports/
    ├── __init__.py
    ├── models.py               # FrameReport, CumulativeStats
    └── generators.py           # 报告生成器
```

## 文件清单

### 1. domain/detection/models.py

| 项目 | 值 |
|---|---|
| 作用 | 检测结果领域模型 |
| 所属层 | domain |
| 依赖模块 | dataclasses, numpy |
| 耦合风险 | 低 |
| 未来扩展 | 添加新检测属性 |

数据结构：
- `Detection`：xyxy, confidence, class_id, class_name
- `Detections`：items list, frame_index, timestamp

### 2. domain/detection/service.py

| 项目 | 值 |
|---|---|
| 作用 | YOLO 检测服务封装 |
| 所属层 | domain |
| 依赖模块 | ultralytics, supervision, numpy |
| 耦合风险 | 低 |
| 未来扩展 | 多模型切换、模型热更新 |

核心职责：加载 YOLO 模型、MPS 设备管理、执行推理、结果转换、类别过滤

公开 API：
- `DetectionService(model_path, device, confidence_threshold, iou_threshold)`
- `detect(frame) -> Detections`
- `get_class_names() -> dict[int, str]`

### 3. domain/tracking/models.py

| 项目 | 值 |
|---|---|
| 作用 | 轨迹领域模型 |
| 所属层 | domain |
| 依赖模块 | dataclasses |
| 耦合风险 | 低 |
| 未来扩展 | 添加轨迹属性（速度、方向） |

数据结构：`Track` — tracker_id, class_id, class_name, confidence, xyxy, first_seen, last_seen

### 4. domain/tracking/service.py

| 项目 | 值 |
|---|---|
| 作用 | ByteTrack 跟踪服务封装 |
| 所属层 | domain |
| 依赖模块 | supervision, domain.detection.models, domain.tracking.models |
| 耦合风险 | 低 |
| 未来扩展 | 多跟踪器切换（BoT-SORT 等） |

核心职责：初始化 ByteTrack、更新跟踪状态、管理活跃轨迹、过滤丢失轨迹

公开 API：
- `TrackingService(frame_rate, track_buffer, matching_threshold)`
- `update(detections) -> list[Track]`
- `get_active_tracks() -> list[Track]`
- `reset()`

### 5. domain/zones/models.py

| 项目 | 值 |
|---|---|
| 作用 | 区域领域模型 |
| 所属层 | domain |
| 依赖模块 | dataclasses |
| 耦合风险 | 低 |
| 未来扩展 | 多边形区域、自定义形状 |

数据结构：
- `ZoneConfig`：name, line_start, line_end
- `ZoneStats`：name, in_count, out_count

### 6. domain/zones/service.py

| 项目 | 值 |
|---|---|
| 作用 | LineZone 区域统计服务封装 |
| 所属层 | domain |
| 依赖模块 | supervision, domain.zones.models, domain.detection.models |
| 耦合风险 | 低 |
| 未来扩展 | 多边形区域、多区域联动 |

核心职责：创建 LineZone、触发检测结果、统计进出计数、管理多个区域

公开 API：
- `ZoneService(zones, minimum_crossing_threshold)`
- `trigger(detections) -> list[ZoneStats]`
- `get_stats() -> list[ZoneStats]`
- `reset()`

### 7. domain/reports/models.py

| 项目 | 值 |
|---|---|
| 作用 | 报告领域模型 |
| 所属层 | domain |
| 依赖模块 | dataclasses |
| 耦合风险 | 低 |
| 未来扩展 | 添加新报告字段 |

数据结构：
- `FrameReport`：frame_index, timestamp_sec, fps, active_tracks, zone_stats, total_in, total_out
- `CumulativeStats`：total_frames, total_unique_tracks, zone_stats, avg_fps, processing_time_sec

### 8. domain/reports/generators.py

| 项目 | 值 |
|---|---|
| 作用 | 报告生成器 |
| 所属层 | domain |
| 依赖模块 | domain.reports.models, domain.tracking.models, domain.zones.models |
| 耦合风险 | 低 |
| 未来扩展 | 多种报告格式 |

核心职责：汇总数据、生成 FrameReport、生成 CumulativeStats

公开 API：
- `ReportGenerator(report_interval)`
- `add_frame(frame_index, timestamp, tracks, zone_stats, fps)`
- `should_report() -> bool`
- `generate_frame_report() -> FrameReport`
- `generate_cumulative_stats() -> CumulativeStats`

## 测试计划

### 单元测试

- test_detection_models.py (~5 tests)
- test_detection_service.py (~8 tests)
- test_tracking_models.py (~3 tests)
- test_tracking_service.py (~6 tests)
- test_zone_models.py (~3 tests)
- test_zone_service.py (~5 tests)
- test_report_models.py (~3 tests)
- test_report_generators.py (~6 tests)

### 集成测试

- test_cv_pipeline.py：完整 CV 流水线 (~3 tests)

### 测试策略

- 模拟 YOLO 推理结果（不需要真实模型）
- 模拟 ByteTrack 更新
- 模拟 LineZone 触发
- 验证数据流正确性

## 验证清单

- [ ] `python -c "from domain.detection import DetectionService"` 成功
- [ ] `python -c "from domain.tracking import TrackingService"` 成功
- [ ] `python -c "from domain.zones import ZoneService"` 成功
- [ ] `python -c "from domain.reports import ReportGenerator"` 成功
- [ ] MPS 可用：`torch.backends.mps.is_available()` 返回 True
- [ ] YOLO 模型加载成功（MPS 设备）
- [ ] 检测结果正确转换
- [ ] 跟踪 ID 正确分配
- [ ] LineZone 计数正确更新
- [ ] FrameReport 结构正确
- [ ] 所有单元测试通过
- [ ] 集成测试通过

## 工作量评估

```yaml
模块: Phase 1 - CV 核心引擎
复杂度: 中
预计开发: 2-3 天
依赖模块:
  - supervision (Detections, ByteTrack, LineZone)
  - ultralytics (YOLO)
  - numpy
测试成本: 中（需要模拟数据）
风险: 中（MPS 兼容性）
未来扩展:
  - 多模型切换
  - 多跟踪器支持
  - 多边形区域
```

## 技术债检查

```yaml
Phase: 1
当前技术债: 无
耦合情况: Domain 层内部模块间有轻度依赖
扩展风险: 低
是否需要重构: 否
建议拆分方案: 无
```
