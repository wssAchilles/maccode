# Real Video Analysis Summary

本文件记录真实交通视频数据集的当前验证状态，用于答辩时说明系统已经从 synthetic demo 进入真实视频闭环。

## Dataset Scope

- 数据目录：`data/tests/real_video_clips`
- 当前黄金样片：`026`、`042`、`054`、`058` 四段真实视频。
- 场景参数：`data/tests/calibration_presets.yaml`、`data/tests/camera_profiles.yaml`
- 运行路径：YOLO 检测 -> `supervision.ByteTrack` 跟踪 -> `LineZone` 统计 -> 单应性世界坐标 -> Kalman 速度估计 -> 误差传播 -> Greenshields 交通流指标。
- 当前黄金样片 smoke 命令：

```bash
 .venv/bin/python backend/scripts/analyze_real_videos.py \
  --clips \
    026_complex_signal_day_wide_0115s_30s.mp4 \
    042_pedestrian_crowd_high_view_0270s_30s.mp4 \
    054_dense_city_traffic_4k_elevated_0030s_30s.mp4 \
    058_dense_city_traffic_4k_elevated_0150s_30s.mp4 \
  --max-frames 30 \
  --frame-stride 30 \
  --output-dir data/outputs/golden_acceptance_smoke
```

## Golden Calibration QA

当前四个黄金样片已经生成 QA 图片和量化摘要：

- QA 目录：`data/outputs/calibration_qa/`
- 采点包：`data/outputs/golden_calibration_packet/`
- 分析输出：`data/outputs/golden_acceptance_smoke/`
- 数学模型卡片：`data/outputs/golden_acceptance_smoke/math_model_cards/`
- 验收表：`data/outputs/golden_acceptance_table/golden_acceptance_table.md`

当前验收结果是 `4/4 trusted`。四个黄金样片都已经使用 `agent_cv_geometry_prior_homography` 生成标定包：OpenCV 候选地面线段提供视觉几何证据，`traffic_standard_visual_prior` 提供米制尺度锚点，独立验证线段通过门禁后才允许 Homography Grid 渲染。

| Clip | Calibration source | Annotation method | Quality | Validation max error | Detected line groups | Grid |
| --- | --- | --- | --- | ---: | ---: | --- |
| `026_complex_signal_day_wide_0115s_30s.mp4` | `video_manual_preset` | `agent_cv_geometry_prior_homography` | `excellent` | 0.15 px | 7 / 15 | rendered |
| `042_pedestrian_crowd_high_view_0270s_30s.mp4` | `video_manual_preset` | `agent_cv_geometry_prior_homography` | `excellent` | 0.35 px | 16 / 2 | rendered |
| `054_dense_city_traffic_4k_elevated_0030s_30s.mp4` | `video_manual_preset` | `agent_cv_geometry_prior_homography` | `excellent` | 0.13 px | 15 / 9 | rendered |
| `058_dense_city_traffic_4k_elevated_0150s_30s.mp4` | `video_manual_preset` | `agent_cv_geometry_prior_homography` | `excellent` | 0.18 px | 5 / 19 | rendered |

重要口径：这些视频来自公开数据集，本项目没有声称 field survey。米制坐标由可解释的交通规范先验锚定，例如车道宽、道路边界、车辆尺寸和人行通道宽度；YAML 中的 `scale_prior.kind` 明确记录为 `traffic_standard_visual_prior`。

## Verification Result

最近一次 golden acceptance smoke 成功处理四个黄金样片，并在本地推理后端完成检测、跟踪、标定门禁和验收表生成：

- Successful clips: 4 / 4
- Defense-ready clips: 4 / 4
- Output artifact: `data/outputs/golden_acceptance_smoke/summary.json`
- Processed MP4: `data/outputs/golden_acceptance_smoke/processed_videos/`
- Math cards: `data/outputs/golden_acceptance_smoke/math_model_cards/`

核心验收命令：

```bash
.venv/bin/python backend/scripts/run_golden_calibration_acceptance.py \
  --run-analysis \
  --max-frames 1 \
  --frame-stride 900 \
  --device auto \
  --model yolo11n.pt \
  --strict
```

速度与交通流结果现在以 `calibration_trusted=true` 的黄金机位为主展示对象。系统仍保留保守门禁：如果后续上传视频无法匹配可信固定机位或验证误差超过阈值，前端和 processed MP4 会自动禁止渲染 Homography Grid，并把速度声明降级为低置信。

## Calibration Sensitivity

当前脚本会为每段真实视频输出 `sensitivity` 字段，用于说明世界尺度误差对测速结果的影响。因为平面单应性将像素位移映射到世界距离，若标定尺度存在 `s%` 的误差，则速度估计也近似存在 `s%` 的线性尺度误差。

| Clip | Calibration source | Trusted | Scale uncertainty | Validation max error |
| --- | --- | --- | ---: | ---: |
| `026_complex_signal_day_wide_0115s_30s.mp4` | video_manual_preset | true | 9% | 0.15 px |
| `042_pedestrian_crowd_high_view_0270s_30s.mp4` | video_manual_preset | true | 12% | 0.35 px |
| `054_dense_city_traffic_4k_elevated_0030s_30s.mp4` | video_manual_preset | true | 10% | 0.13 px |
| `058_dense_city_traffic_4k_elevated_0150s_30s.mp4` | video_manual_preset | true | 10% | 0.18 px |

## Mathematical Calibration Policy

当前真实视频已有固定机位 profile 和 agent 视觉先验标定包。系统采用可解释的工程校准策略：

- 每个黄金样片使用 OpenCV Canny/Hough 候选线段提取道路几何，把线段按纵向/横向主方向分组，并记录到 `auto_geometry`。
- 每类场景使用独立 `camera_profile`，固定世界宽度、道路长度、过线位置和位置 RMSE floor。
- `calibration_presets.yaml` 与 `camera_profiles.yaml` 将场景参数从代码外置；同一固定机位通过验收后可复用为 `camera_manual_preset`。
- `scale_constraints` 记录车道宽、人行通道宽、车辆尺寸等交通规范先验，并明确 `not field surveyed`。
- 如果存在可信 `video_manual_preset` 或 `camera_manual_preset`，系统才允许输出 Homography Grid；否则只保留检测、跟踪和降级统计。
- RANSAC 单应性输出 `inlier_count`、重投影 RMSE、双向误差和质量等级；独立验证线段不能复用拟合点。
- `position_rmse_floor_m` 作为工业保守项进入速度误差传播，避免出现“数学上 RMSE 很低但物理标定不可信”的假象。
- 速度输出同时给 `speed_kmh`、`speed_uncertainty_kmh`、`speed_confidence`，让 LLM 和前端能区分高置信与低置信结果。

## Defense Narrative

这套验证说明项目不是单纯调用检测模型，而是把非结构化视频转化为结构化物理量：

```text
真实视频帧
  -> YOLO 目标检测
  -> supervision ByteTrack 目标身份保持
  -> 单应性矩阵映射到世界平面
  -> 类别路由 Kalman 状态估计
  -> 速度、不确定性、置信度
  -> Greenshields 宏观交通流状态
  -> LLM 动态上下文推理
```

## Physical Semantic Interface

边缘端最终向 LLM 输出的不是检测框，而是物理语义 JSON。当前合同已经覆盖以下字段：

| 物理量 | JSON 字段 | 单位 | 模型来源 |
| --- | --- | --- | --- |
| 瞬时真实速度 | `active_tracks[].speed_kmh` | km/h | Model 1 单应性 + Model 3 Kalman + Model 10 路由 |
| 二维地面绝对坐标 | `active_tracks[].ground_x_m`, `active_tracks[].ground_y_m` | m | Model 1 单应性地面逆投影 |
| 速度置信区间 | `active_tracks[].speed_confidence_interval_kmh` | km/h | Model 6 误差传播 |
| 二维速度向量 | `active_tracks[].velocity_x_mps`, `active_tracks[].velocity_y_mps` | m/s | Model 3 Kalman 状态向量 |
| 航向角 | `active_tracks[].heading_deg` | degree | 速度向量反正切 |
| 加速度 | `active_tracks[].acceleration_mps2` | m/s^2 | 相邻速度差分 |
| 区域拥挤人数 | `regional_people_count.people_count` | person | 直接检测计数，拥挤时预留 Model 9 密度积分降级 |
| 设施状态与交互语义 | `infrastructure_semantics` | enum / bool | Model 10 静态设施路由 |
| 最小跟车时距 | `safety_metrics.min_time_headway_sec` | s | 轨迹间距 / 自车速度 |
| 近似碰撞时距 | `safety_metrics.min_time_to_collision_sec` | s | 轨迹间距 / 相对速度 |

示例语义片段：

```json
{
  "active_tracks": [
    {
      "tracker_id": 12,
      "speed_kmh": 75.0,
      "speed_confidence_interval_kmh": [71.0, 79.0],
      "ground_x_m": 18.4,
      "ground_y_m": 42.7,
      "velocity_x_mps": 3.2,
      "velocity_y_mps": 1.1,
      "heading_deg": 19.0,
      "acceleration_mps2": -0.4
    }
  ],
  "regional_people_count": {
    "people_count": 38,
    "estimation_method": "density_integral_fallback"
  },
  "infrastructure_semantics": {
    "traffic_light_state": "unknown",
    "violation_on_crosswalk": false
  },
  "safety_metrics": {
    "min_time_headway_sec": 1.2,
    "min_time_to_collision_sec": 3.8,
    "risk_level": "elevated"
  }
}
```

当前红绿灯 `red/green` 状态仍是 `unknown`，这是有意保守：YOLO 只能稳定给出 traffic light 类别，颜色状态需要信号灯 ROI 分类器或人工规则。答辩时可以把它讲成下一步扩展，而不是把检测类别伪装成状态识别。

## LLM Context Contract

动态上下文组装器会把上述物理量打包成 LLM 可读的轻量 JSON，而不是把原始视频或检测框直接发到云端。当前 payload 包含：

- `physical_state.regional_people_count`
- `physical_state.infrastructure_semantics`
- `physical_state.safety_metrics`
- `motion_routes[].ground_position_m`
- `motion_routes[].velocity_mps`
- `motion_routes[].heading_deg`
- `motion_routes[].acceleration_mps2`
- `motion_routes[].speed_confidence_interval_kmh`
- `risk_signals[]` 中的超速、短时距/碰撞风险、交通基础设施存在性

这样云端大模型只负责常识推理和决策表达，边缘端负责所有可验证的视觉、几何、运动学与误差传播计算，符合端云协同的工程边界。

答辩时应主动说明：当前代码门禁已经避免“假网格”。四个黄金机位已通过 agent 视觉先验标定与独立验证；其它未标定视频仍需先进入同一门禁，不能直接复用网格。

## Agent-Assisted Calibration Workflow

工业级测速的关键不是盲信 YOLO，而是把相机视角固定到真实道路平面。当前仓库提供了标定资产生成工具：

```bash
.venv/bin/python backend/scripts/build_golden_calibration_packet.py \
  --frame-index 1 \
  --coordinate-step 160
```

该命令会输出：

- `data/outputs/golden_calibration_packet/keyframes/*.jpg`：四个黄金样片的关键帧。
- `data/outputs/golden_calibration_packet/coordinate_guides/*.jpg`：带像素坐标参考线的采点图。
- `data/outputs/golden_calibration_packet/qa/*_qa.jpg`：当前控制点、验证线段和网格状态 QA 图。
- `data/outputs/golden_calibration_packet/README.md`：逐样片采点建议和当前 trusted 状态。
- `data/outputs/golden_calibration_packet/golden_calibration_packet.json`：机器可读采点清单。

当前黄金样片优先使用轻量 OpenCV 自动候选 + 本项目标定工作台闭环。CVAT / Datumaro 可以作为后续批量标注工具，但不会阻塞当前答辩验收。

Agent 标定步骤：

1. 抽取关键帧并用 OpenCV 检测候选地面线段。
2. 过滤天空、建筑立面、车辆和行人，仅保留道路/人行地面 ROI。
3. 根据车道宽、人行通道宽、车辆尺寸等交通规范先验建立米制世界坐标。
4. 生成 8-10 个控制点、2 条以上独立验证线段和 1 个 `road_plane_polygon`。
5. 导入 `calibration_presets.yaml`，再晋升通过门禁的固定机位到 `camera_profiles.yaml`。
6. 运行 QA 与 golden acceptance，确认网格贴合、验证误差和 processed MP4 全部达标。

```bash
.venv/bin/python backend/scripts/build_calibration_qa.py \
  --clips \
    026_complex_signal_day_wide_0115s_30s.mp4 \
    042_pedestrian_crowd_high_view_0270s_30s.mp4 \
    054_dense_city_traffic_4k_elevated_0030s_30s.mp4 \
    058_dense_city_traffic_4k_elevated_0150s_30s.mp4 \
  --frame-index 1
```

该命令会输出：

- `data/outputs/calibration_qa/*_qa.jpg`
- `data/outputs/calibration_qa/calibration_qa_summary.json`
- `data/outputs/calibration_qa/calibration_qa_summary.md`

答辩时可以明确说明：项目没有把公开数据集伪装成实地测绘，而是用交通规范先验建立可解释的米制锚点，并用独立验证线段证明 Homography Grid 不是硬编码装饰。

## Current Benchmark Workflow

当前阶段不再使用早期单个主展示候选，而是围绕四个黄金样片做统一验收：

```bash
.venv/bin/python backend/scripts/build_calibration_qa.py \
  --clips \
    026_complex_signal_day_wide_0115s_30s.mp4 \
    042_pedestrian_crowd_high_view_0270s_30s.mp4 \
    054_dense_city_traffic_4k_elevated_0030s_30s.mp4 \
    058_dense_city_traffic_4k_elevated_0150s_30s.mp4 \
  --frame-index 1

.venv/bin/python backend/scripts/analyze_real_videos.py \
  --clips \
    026_complex_signal_day_wide_0115s_30s.mp4 \
    042_pedestrian_crowd_high_view_0270s_30s.mp4 \
    054_dense_city_traffic_4k_elevated_0030s_30s.mp4 \
    058_dense_city_traffic_4k_elevated_0150s_30s.mp4 \
  --max-frames 30 \
  --frame-stride 30 \
  --output-dir data/outputs/golden_acceptance_smoke

.venv/bin/python backend/scripts/build_golden_acceptance_table.py
```

质量门禁不是为了让所有样本都“好看”，而是为了体现工程诚实性：没有可信标定的样片可以展示 detection/tracking/traffic-flow 的工程闭环，但不能展示 Homography Grid 作为“数学证明”。只有 QA 摘要中 `Trusted=true` 且 `validation_max_error_px < 15` 的样片，才能作为最终答辩主展示。

## Workbench Workflow

前端“人工标定”页现在用于四个黄金机位的真实数据采集：

- 选择或上传 MP4，播放到稳定关键帧。
- 捕获当前视频帧作为标定图。
- 点击 6-10 个真实地面控制点，输入米制世界坐标。
- 使用“前四点生成地面区域”生成 `road_plane_polygon_world`。
- 使用结构化验证段生成器录入独立 `validation_segments`，并在标定图上直接检查线段是否贴合真实车道线、斑马线或人行道边界。
- 声明 trusted 后保存 YAML；后端会重新计算 `world_to_pixel_rmse_px`、`pixel_to_world_rmse_m`、`validation_max_error_px`。

保存结果仍要遵守后端门禁：声明 trusted 不等于真正 trusted。只有独立验证段误差达标，诊断结果里的 `calibration_trusted` 才会变为 `true`，对应样片才会生成 Homography Grid。
