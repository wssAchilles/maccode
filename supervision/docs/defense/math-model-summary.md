# Speed Estimation Defense Summary

当前实现已经从“可运行测速”升级为答辩主线数学模型：RANSAC 单应性、类别路由 Kalman 状态估计、速度误差传播、Greenshields 宏观交通流指标。

## Implemented Core

- 几何层：DLT 构造 `Ah = 0`，SVD 求解单应性矩阵 `H`，RANSAC 剔除外点后用内点重估。
- 质量层：输出 `inlier_mask`、`inlier_count`、重投影 `RMSE`、`calibration_quality`。
- 状态层：Kalman 状态向量 `[x, y, vx, vy]`，车辆使用小过程噪声，行人使用大过程噪声。
- 误差层：由位置 RMSE、时间不确定性、位移长度传播到 `speed_uncertainty_kmh` 与 `speed_confidence`。
- 宏观层：计算 `flow q`、`density k`、空间平均速度，并用 Greenshields 模型输出拥堵等级。

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
