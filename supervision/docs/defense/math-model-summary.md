# Speed Estimation Defense Summary

当前实现已经从“可运行测速”升级为答辩主线数学模型：RANSAC 单应性、类别路由 Kalman 状态估计、速度误差传播、Greenshields 宏观交通流指标。

## Implemented Core

- 几何层：DLT 构造 `Ah = 0`，SVD 求解单应性矩阵 `H`，RANSAC 剔除外点后用内点重估。
- 质量层：输出 `inlier_mask`、`inlier_count`、`pixel_to_world_rmse_m`、`world_to_pixel_rmse_px`、独立验证线段误差和 `calibration_quality`。
- 状态层：Kalman 状态向量 `[x, y, vx, vy]`，车辆使用小过程噪声，行人使用大过程噪声。
- 误差层：由位置 RMSE、时间不确定性、位移长度传播到 `speed_uncertainty_kmh` 与 `speed_confidence`。
- 宏观层：计算 `flow q`、`density k`、空间平均速度，并用 Greenshields 模型输出拥堵等级。
- 展示层：只有 `camera_manual_preset` / `video_manual_preset` 且独立验证误差通过门禁时，才允许渲染 Homography Grid。

## Homography Trust Gate

Homography Grid 不是 UI 装饰，而是数学模型的可视化证据。当前系统使用双门禁避免“假网格”：

- `scene_profile_preset` 永不生成 Homography Grid。
- `calibration_trusted: true` 只是一项声明，必须同时满足 `validation_max_error_px < 15` 才会生效。
- `validation_segments` 必须是独立车道线、停止线、斑马线边缘或人行道边界；不能只复用控制点。
- 未通过门禁时，前端和 processed MP4 显示“需要人工可信标定”，不画网格。
- QA 产物位于 `data/outputs/calibration_qa/`，用于逐样片检查控制点、验证线段和网格状态。

## Agent Visual-Prior Calibration

四个黄金样片来自公开视频，项目不声称实地测绘。当前采用 `traffic_standard_visual_prior` 建立米制尺度：

- OpenCV Canny/Hough 候选线段检测车道线、路缘线、停止线、斑马线或铺装边界。
- 线段按道路主方向聚类为 longitudinal / lateral 两组，并写入 `auto_geometry` 作为可审计证据。
- 米制尺度由通用交通工程先验锚定，例如 3.0-3.75m 车道宽、人行通道宽度、车辆外廓尺寸和铺装模块。
- 每个样片输出 8-10 个控制点、3 条独立验证线段和 `road_plane_polygon`，最终导入 `golden-calibration-picks.json` 与 YAML。
- CVAT / Datumaro 可用于后续批量复核，但当前答辩闭环优先使用轻量 OpenCV 自动候选加本项目标定工作台，不阻塞本地运行。

这一路线的关键不是“自动猜一个好看的梯形”，而是把每个尺度假设、几何候选和验证误差写入数据契约，允许答辩时逐项追溯。

## Model Chain

```text
像素坐标
  -> RANSAC 单应性 H
  -> 世界坐标
  -> 类别路由 Kalman 状态估计
  -> 速度 + 不确定性 + 置信度
  -> Greenshields 交通流指标
  -> Dynamic Context
  -> LLM 路况推理
```

## Defense Talking Points

- RANSAC 让标定不依赖“每个点都精确”，能解释真实场景中人工点选误差和外点。
- Kalman 不是普通平滑，而是把目标运动建模为状态空间估计；车辆和行人使用不同 Q，体现物理属性差异。
- 速度结果不只给一个数，还给不确定性和置信度，能主动说明短位移、低 FPS、标定误差带来的风险。
- 单车速度进一步升维为道路交通流状态，支撑“空间智能认知与决策引擎”的项目定位。

## Deferred Extensions

- EKF/UKF 用于非线性运动和更复杂相机模型。
- 光流辅助速度验证用于检测框抖动或跟踪 ID switch 时的冗余校验。
- 三维射影补偿用于坡道、桥梁、非平坦路面。
- LWR 当前作为答辩理论解释，暂不实现 PDE 数值求解。
