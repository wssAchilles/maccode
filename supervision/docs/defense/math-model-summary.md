# Speed Estimation Defense Summary

前期实现采用进阶 B：RANSAC/鲁棒思路下的单应性模型、轨迹历史速度估算、平滑与异常过滤、误差指标输出。

## Implemented Core

- 单应性矩阵 `H` 将像素点 `(u, v)` 映射到世界坐标 `(X, Y)`。
- DLT 构造 `Ah = 0`，用 SVD 取最小奇异值对应向量并归一化为 3x3 矩阵。
- 重投影 RMSE 用于标定质量判断。
- 速度公式：`speed_kmh = distance_m / delta_t_sec * 3.6`。
- 防抖策略：最小位移过滤、最大速度过滤、中位数平滑。

## Deferred High-Score Extensions

- EKF/UKF 状态估计。
- 光流辅助速度验证。
- 三维射影补偿非平坦路面。
- Greenshields/LWR 宏观交通流建模。
