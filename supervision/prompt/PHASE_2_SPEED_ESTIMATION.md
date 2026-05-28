# Phase 2: 速度估算（硬核算法）

## 目标

实现基于单应性变换的速度估算模块。这是算法硬核部分，涉及纯数学推导。

复杂度：高 | 风险：高 | 预计时间：2-4 天

## 业务流

```
视频帧 + 检测结果
    ↓
提取目标像素坐标（边界框中心）
    ↓
ViewTransformer 单应性变换
    ↓ pixel → world
真实世界坐标（米）
    ↓
计算相邻帧位移
    ↓
位移 / 时间间隔 = 速度
    ↓
滑动窗口平滑
    ↓
异常值过滤
    ↓
速度结果（km/h）
```

## 数学原理

### 单应性变换

单应性矩阵 H 将像素坐标 (u,v) 映射到真实世界坐标 (X,Y)。求解 H 需要 4+ 对对应点。使用 `cv2.findHomography()` 求解。

### 透视变换

得到 H 后，使用 `cv2.perspectiveTransform()` 将像素坐标转换为世界坐标。

### 速度计算

```
位移 = √((X₂-X₁)² + (Y₂-Y₁)²)   # 世界坐标，单位：米
时间 = (frame₂ - frame₁) / fps     # 单位：秒
速度_m/s = 位移 / 时间
速度_kmh = 速度_m/s × 3.6
```

### 防抖动处理

1. 滑动窗口：取最近 N 帧速度的中位数
2. 最小位移阈值：位移 < 0.1m 视为静止
3. 异常值过滤：速度 > 200 km/h 视为异常
4. 指数移动平均：平滑系数 α=0.3

## 目录结构

```
domain/
├── calibration/
│   ├── __init__.py
│   ├── models.py               # 标定点数据模型
│   └── service.py              # 标定服务
└── speed/
    ├── __init__.py
    ├── models.py               # 速度数据模型
    ├── view_transformer.py     # 单应性变换
    ├── estimator.py            # 速度估算器
    ├── smoothing.py            # 速度平滑算法
    └── filters.py              # 异常值过滤
```

## 文件清单

### 1. domain/calibration/models.py

| 项目 | 值 |
|---|---|
| 作用 | 标定点数据模型 |
| 所属层 | domain |
| 依赖模块 | dataclasses, numpy |
| 耦合风险 | 低 |
| 未来扩展 | 支持更多标定方法 |

数据结构：
- `CalibrationPoint`：pixel_x, pixel_y, world_x, world_y
- `CalibrationConfig`：points list, is_valid

### 2. domain/calibration/service.py

| 项目 | 值 |
|---|---|
| 作用 | 标定服务：验证标定点、计算 H 矩阵 |
| 所属层 | domain |
| 依赖模块 | opencv, numpy |
| 耦合风险 | 低 |
| 未来扩展 | 自动标定、多摄像头标定 |

核心职责：验证标定点数量（≥4）、验证不共线、计算 H 矩阵、计算重投影误差

公开 API：
- `CalibrationService()`
- `validate_points(points) -> bool`
- `compute_homography(pixel_points, world_points) -> np.ndarray`
- `compute_reprojection_error(H, pixel_points, world_points) -> float`

### 3. domain/speed/models.py

| 项目 | 值 |
|---|---|
| 作用 | 速度数据模型 |
| 所属层 | domain |
| 依赖模块 | dataclasses |
| 耦合风险 | 低 |
| 未来扩展 | 添加方向、加速度 |

数据结构：
- `SpeedRecord`：tracker_id, speed_kmh, timestamp, world_x, world_y
- `TrackHistory`：tracker_id, positions list, timestamps list

### 4. domain/speed/view_transformer.py

| 项目 | 值 |
|---|---|
| 作用 | 像素坐标→世界坐标变换 |
| 所属层 | domain |
| 依赖模块 | opencv, numpy |
| 耦合风险 | 低 |
| 未来扩展 | 支持多种变换模型 |

核心职责：存储 H 矩阵、执行透视变换、批量坐标转换

公开 API：
- `ViewTransformer(homography_matrix)`
- `transform_point(pixel_x, pixel_y) -> tuple[float, float]`
- `transform_points(pixel_points) -> np.ndarray`

### 5. domain/speed/estimator.py

| 项目 | 值 |
|---|---|
| 作用 | 速度估算核心算法 |
| 所属层 | domain |
| 依赖模块 | numpy, view_transformer, smoothing, filters |
| 耦合风险 | 中 |
| 未来扩展 | 卡尔曼滤波、3D 速度估算 |

核心职责：维护轨迹历史、计算世界坐标位移、计算速度、应用平滑和过滤

公开 API：
- `SpeedEstimator(view_transformer, fps, smoothing_window, min_displacement, max_speed)`
- `update(tracker_id, pixel_center, timestamp) -> float | None`
- `get_speed(tracker_id) -> float | None`
- `get_all_speeds() -> dict[int, float]`
- `reset()`

### 6. domain/speed/smoothing.py

| 项目 | 值 |
|---|---|
| 作用 | 速度平滑算法 |
| 所属层 | domain |
| 依赖模块 | numpy |
| 耦合风险 | 低 |
| 未来扩展 | 卡尔曼滤波、粒子滤波 |

算法：
- `median_smoothing(values, window_size)` — 中位数平滑
- `exponential_smoothing(values, alpha)` — 指数移动平均
- `moving_average(values, window_size)` — 简单移动平均

### 7. domain/speed/filters.py

| 项目 | 值 |
|---|---|
| 作用 | 异常值过滤 |
| 所属层 | domain |
| 依赖模块 | numpy |
| 耦合风险 | 低 |
| 未来扩展 | 自适应阈值 |

过滤器：
- `min_displacement_filter(displacement, threshold)` — 最小位移过滤
- `max_speed_filter(speed, max_speed)` — 最大速度过滤
- `statistical_outlier_filter(speeds, sigma)` — 统计异常过滤

## 测试计划

### 单元测试

- test_calibration_models.py (~3 tests)
- test_calibration_service.py (~6 tests)
- test_speed_models.py (~3 tests)
- test_view_transformer.py (~5 tests)
- test_speed_estimator.py (~8 tests)
- test_smoothing.py (~4 tests)
- test_filters.py (~4 tests)

### 集成测试

- test_speed_pipeline.py：完整速度估算流水线 (~3 tests)

### 测试数据

需要准备：标定点数据、模拟轨迹数据、预期速度结果

## 验证清单

- [ ] 标定点验证：≥4 点，不共线
- [ ] H 矩阵计算正确
- [ ] 透视变换结果合理
- [ ] 静止目标速度 ≈ 0
- [ ] 匀速运动目标速度稳定
- [ ] 异常值被正确过滤
- [ ] 滑动窗口平滑有效
- [ ] 重投影误差 < 1 像素
- [ ] 所有单元测试通过
- [ ] 集成测试通过

## 工作量评估

```yaml
模块: Phase 2 - 速度估算
复杂度: 高
预计开发: 2-4 天
依赖模块:
  - OpenCV (cv2.findHomography, cv2.perspectiveTransform)
  - numpy
  - domain.tracking (Track)
测试成本: 高（需要标定数据和模拟轨迹）
风险:
  - 透视标定误差
  - Tracker ID 抖动
  - FPS 不稳定
  - 静止目标干扰
未来扩展:
  - 多摄像头融合
  - 3D 速度估算
  - 卡尔曼滤波
  - 自动标定
```

## 技术债检查

```yaml
Phase: 2
当前技术债: 无
耦合情况: SpeedEstimator 依赖 ViewTransformer + Smoothing + Filters
扩展风险: 中（未来可能需要卡尔曼滤波）
是否需要重构: 否（当前设计已支持可插拔平滑算法）
建议拆分方案: 无
```
