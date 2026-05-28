# Real Video Analysis Summary

本文件记录真实交通视频数据集的当前验证状态，用于答辩时说明系统已经从 synthetic demo 进入真实视频闭环。

## Dataset Scope

- 数据目录：`data/tests/real_video_clips`
- 当前轻量验证：按场景 profile 各抽取 1 段，共 4 段真实视频。
- 场景参数：`data/tests/calibration_presets.json`
- 运行路径：YOLO 检测 -> `supervision.ByteTrack` 跟踪 -> `LineZone` 统计 -> 单应性世界坐标 -> Kalman 速度估计 -> 误差传播 -> Greenshields 交通流指标。
- 运行命令：

```bash
MPLCONFIGDIR=/private/tmp/mpl .venv/bin/python backend/scripts/analyze_real_videos.py \
  --limit 4 \
  --sample-per-profile 1 \
  --max-frames 6 \
  --frame-stride 30 \
  --confidence 0.35 \
  --device cpu
```

## Verification Result

| Scene profile | Clip | Tracks | Space mean speed | Density | Congestion | Position RMSE floor |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| wide_signalized_intersection | `023_complex_signal_day_wide_0010s_30s.mp4` | 5 | 4.07 km/h | 66.67 veh/km | congested_flow | 1.5 m |
| red_light_static | `028_red_light_static_0008s_30s.mp4` | 2 | 7.40 km/h | 30.77 veh/km | congested_flow | 1.5 m |
| pedestrian_high_view | `033_pedestrian_crowd_high_view_0000s_30s.mp4` | 3 | 22.89 km/h | 0.00 veh/km | stable_flow | 1.2 m |
| dense_city_traffic_4k | `053_dense_city_traffic_4k_elevated_0000s_30s.mp4` | 2 | 1.08 km/h | 18.18 veh/km | congested_flow | 2.0 m |

## Calibration Sensitivity

当前脚本会为每段真实视频输出 `sensitivity` 字段，用于说明世界尺度误差对测速结果的影响。因为平面单应性将像素位移映射到世界距离，若标定尺度存在 `s%` 的误差，则速度估计也近似存在 `s%` 的线性尺度误差。

| Clip | Calibration source | Scale uncertainty | Space mean speed band |
| --- | --- | ---: | ---: |
| `023_complex_signal_day_wide_0010s_30s.mp4` | scene_profile_preset | 8% | 3.74-4.40 km/h |
| `028_red_light_static_0008s_30s.mp4` | scene_profile_preset | 8% | 6.81-7.99 km/h |
| `033_pedestrian_crowd_high_view_0000s_30s.mp4` | scene_profile_preset | 8% | 21.06-24.72 km/h |
| `053_dense_city_traffic_4k_elevated_0000s_30s.mp4` | scene_profile_preset | 12% | 0.95-1.21 km/h |

Aggregate result:

- Successful clips: 4 / 4
- Average speed: 3.74 km/h
- Average speed confidence: 0.39
- MPS status in this run: built but unavailable, CPU fallback used
- Output artifact: `data/outputs/real_video_analysis/summary.json`
- Benchmark report: `data/outputs/real_video_analysis/benchmark_report.md`

## Mathematical Calibration Policy

当前真实视频没有实测地面控制点，因此绝对速度不能被包装成执法级精度。系统采用可解释的工程校准策略：

- 每类场景使用独立 `SceneProfile`，固定世界宽度、道路长度、过线位置和位置 RMSE floor。
- `calibration_presets.json` 将场景参数从代码外置，便于后续替换为人工测量的逐视频标定。
- 如果 `video_calibrations` 中存在精确到文件名的点位配置，系统会优先使用逐视频人工标定；否则才回退到场景级 profile。
- RANSAC 单应性仍输出 `inlier_count`、重投影 RMSE 和质量等级，但启发式点位自身不能替代人工标定。
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

答辩时应主动说明：当前演示级标定用于证明数学链路和系统架构，若要达到执法或工程验收级测速，需要在前端加入人工标定点选择流程，并用已知车道宽度、停止线距离或实测控制点重估单应性。

## Next Calibration Upgrade

- 使用 `prepare_calibration_assets.py` 为真实视频导出标定帧和逐视频 preset 模板。
- 将现有 profile 级 `calibration_presets.json` 扩展为逐视频 preset，记录人工点位、世界坐标、道路长度和车道宽度。
- 前端增加 4 点或 6 点标定界面，导出 `CalibrationConfig`。
- 对同一视频比较 heuristic profile 与 manual calibration 的速度差异，形成答辩误差分析表。
- 增加 longer-window benchmark，至少处理 10-30 秒片段，提升 Kalman 速度稳定性和过线流量统计可信度。

## Manual Calibration Workflow

工业级测速的关键不是盲信 YOLO，而是把相机视角固定到真实道路平面。当前仓库提供了标定资产生成工具：

```bash
MPLCONFIGDIR=/private/tmp/mpl .venv/bin/python backend/scripts/prepare_calibration_assets.py \
  --input-dir data/tests/real_video_clips \
  --output-dir data/outputs/calibration_assets \
  --limit 4 \
  --frame-index 1
```

该命令会输出：

- `data/outputs/calibration_assets/calibration_frames/*.jpg`：逐视频标定参考帧。
- `data/outputs/calibration_assets/calibration_previews/*_preview.jpg`：带编号控制点、世界坐标和标定四边形的预览图。
- `data/outputs/calibration_assets/video_calibration_templates.json`：逐视频 `video_calibrations` 模板。

人工调参步骤：

1. 打开导出的 JPG 标定帧，选取路面上 4 个以上不共线控制点。
2. 将点击到的 `pixel_x/pixel_y` 写入模板。
3. 用车道宽度、停止线距离、斑马线宽度等真实尺度填写 `world_x/world_y`。
4. 把该视频条目复制进 `data/tests/calibration_presets.json` 的 `video_calibrations`。
5. 重新运行真实视频分析脚本；报告中的 `calibration.source` 会从 `scene_profile_preset` 变为 `video_manual_preset`。
6. 运行标定校验脚本，确认点位足够、不共线、重投影误差和尺度不确定性可接受。

```bash
.venv/bin/python backend/scripts/validate_calibration_presets.py \
  --input data/tests/calibration_presets.json \
  --output-dir data/outputs/calibration_validation
```

该命令会输出：

- `data/outputs/calibration_validation/calibration_validation.json`
- `data/outputs/calibration_validation/calibration_validation.md`

答辩时可以明确说明：场景级 preset 证明系统数学链路，逐视频人工标定则是迈向工程验收级测速的关键步骤。

## Benchmark Workflow

真实视频分析完成后，使用 benchmark 汇总脚本生成答辩表格：

```bash
.venv/bin/python backend/scripts/summarize_real_video_benchmark.py \
  --input data/outputs/real_video_analysis/summary.json \
  --output-dir data/outputs/real_video_analysis
```

该脚本输出：

- `benchmark_summary.json`：机器可读的逐场景测速、置信度、风险、标定来源和性能摘要。
- `benchmark_report.md`：可直接复制到答辩材料的 Markdown 表格。
- `quality_status`：基于速度置信度、速度不确定性、处理 FPS、是否使用人工标定等条件给出 `pass/warn/fail`。

当前 benchmark 的一个关键结论是：宽路口短窗口样本的速度不确定性明显偏高。这不是要隐藏的问题，而是答辩中的专业点：它证明系统不仅输出速度，还能揭示标定误差、短位移、跟踪抖动对测速可信度的影响，并给出人工标定和长窗口分析的改进路线。

实现上，交通流均速只使用当前帧仍处于 active 状态的 track 速度记录。若当前帧没有可测速目标，benchmark 中的 mean speed band 会显示为 `N/A`，避免用历史轨迹污染当前宏观交通流判断。

质量门禁不是为了让所有样本都“好看”，而是为了体现工程诚实性：`warn` 样本适合主展示，`fail` 样本适合用于误差分析和调参说明。当前结果中 `028_red_light_static_0008s_30s.mp4` 只有 `demo_calibration` 警告，适合作为答辩主展示候选；宽路口和 4K 密集车流更适合作为“为什么需要人工标定和长窗口”的反例。

主展示候选可以用显式 clip 命令稳定复现：

```bash
MPLCONFIGDIR=/private/tmp/mpl .venv/bin/python backend/scripts/run_real_video_pipeline.py \
  --output-dir data/outputs/main_demo_pipeline \
  --clips 028_red_light_static_0008s_30s.mp4 \
  --max-frames 24 \
  --frame-stride 10 \
  --confidence 0.35 \
  --device cpu
```

该一键流水线会生成：

- `pipeline_manifest.json`
- `calibration_assets/video_calibration_templates.json`
- `calibration_assets/calibration_frames/*.jpg`
- `calibration_assets/calibration_previews/*_preview.jpg`
- `calibration_validation/calibration_validation.md`
- `analysis/summary.json`
- `analysis/benchmark_report.md`

流水线完成后，可以生成紧凑答辩包：

```bash
.venv/bin/python backend/scripts/build_defense_packet.py \
  --pipeline-dir data/outputs/main_demo_pipeline \
  --output-dir data/outputs/defense_packet
```

答辩包输出：

- `data/outputs/defense_packet/README.md`
- `data/outputs/defense_packet/defense_packet_summary.json`

其中 README 会列出主展示视频、质量状态、平均速度置信度、速度不确定性、关键产物路径，以及人工标定的下一步动作。

也可以手动拆分执行：

```bash
MPLCONFIGDIR=/private/tmp/mpl .venv/bin/python backend/scripts/prepare_calibration_assets.py \
  --input-dir data/tests/real_video_clips \
  --output-dir data/outputs/main_demo_calibration_assets_single \
  --clips 028_red_light_static_0008s_30s.mp4 \
  --frame-index 1

MPLCONFIGDIR=/private/tmp/mpl .venv/bin/python backend/scripts/analyze_real_videos.py \
  --output-dir data/outputs/main_demo_analysis \
  --clips 028_red_light_static_0008s_30s.mp4 \
  --max-frames 24 \
  --frame-stride 10 \
  --confidence 0.35 \
  --device cpu

.venv/bin/python backend/scripts/summarize_real_video_benchmark.py \
  --input data/outputs/main_demo_analysis/summary.json \
  --output-dir data/outputs/main_demo_analysis
```

当前长窗口主展示候选结果：平均速度置信度约 0.70，处理 FPS 约 10，但由于仍使用 `scene_profile_preset`，平均速度不确定性约 17 km/h，质量门禁仍会判定为 `fail`。这说明长窗口能改善跟踪稳定性，但不能替代人工标定；若要把它提升为最终主展示，应优先给该视频录入逐视频地面控制点。

主展示候选的标定预览图位于：`data/outputs/main_demo_calibration_assets_single/calibration_previews/028_red_light_static_0008s_30s_preview.jpg`。这张图可用于人工核对 P1-P4 是否贴合真实道路平面，并把修正后的像素点写回 `video_calibrations`。

## Parameter Tuning Matrix

为了避免“凭感觉调参”，当前仓库提供真实视频参数扫描脚本：

```bash
MPLCONFIGDIR=/private/tmp/mpl .venv/bin/python backend/scripts/tune_real_video_parameters.py \
  --output-dir data/outputs/main_demo_tuning \
  --clip 028_red_light_static_0008s_30s.mp4 \
  --confidences 0.30,0.40 \
  --frame-strides 8,12 \
  --max-frames-values 18 \
  --device cpu
```

该脚本会对每组参数完整运行：

```text
YOLO -> supervision ByteTrack -> LineZone -> Homography -> Kalman -> Error Propagation -> Traffic Flow -> Safety Metrics
```

并输出：

- `data/outputs/main_demo_tuning/tuning_summary.json`
- `data/outputs/main_demo_tuning/tuning_report.md`

当前主展示视频的调参结论：

| Confidence | Frame stride | Max frames | Quality | Score | Speed tracks | Avg confidence | Avg uncertainty | Physics | FPS |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.30 | 12 | 18 | warn | 0.828 | 2 | 0.820 | 3.56 km/h | 1.00 | 22.02 |
| 0.40 | 12 | 18 | warn | 0.823 | 2 | 0.836 | 4.75 km/h | 1.00 | 23.58 |
| 0.40 | 8 | 18 | fail | 0.581 | 2 | 0.815 | 25.48 km/h | 1.00 | 21.71 |
| 0.30 | 8 | 18 | fail | 0.564 | 2 | 0.815 | 25.48 km/h | 1.00 | 9.98 |

推荐的未人工标定演示参数为：

```text
confidence=0.30, frame_stride=12, max_frames=18
```

它在当前 demo 标定条件下只剩 `demo_calibration` 警告，不再触发 `high_speed_uncertainty`。这说明短窗口速度误差不仅来自检测模型，也受到采样步长、轨迹时间跨度和透视尺度共同影响。答辩时可以把这张表作为“数学建模调参证据”：系统不是只输出速度，还能解释为什么某些参数组合导致速度不确定性升高。

注意：调参只能降低跟踪抖动和短位移带来的不确定性，不能替代逐视频人工标定。最终工业级绝对测速仍必须满足 `calibration.source = video_manual_preset`。

前端“人工标定”页可直接选择标定帧 JPG，点击 P1-P4 自动生成像素坐标，并导出两种 JSON：

- 片段 JSON：只包含某个视频的 `video_calibrations` entry。
- 完整 preset JSON：带 `schema_version` 和 `video_calibrations` 包装，可作为 `calibration_presets.json` 的候选版本。

导出后不要手工复制粘贴到主配置里，优先使用合并脚本生成候选 preset：

```bash
.venv/bin/python backend/scripts/merge_calibration_preset.py \
  --base data/tests/calibration_presets.json \
  --input path/to/calibration_presets.generated.json \
  --output data/tests/calibration_presets.merged.json \
  --required-clips 028_red_light_static_0008s_30s.mp4
```

该脚本只合并 `video_calibrations`，保留 `scene_profiles`，并立即输出：

- `merged_calibration_validation.json`
- `merged_calibration_validation.md`

如果输入来自自动模板而不是人工点击，校验器会标记 `template_points_not_manual`，不会误判为 `industrial_readiness=ready`。这是工业级验收的关键防线：单应性矩阵数学上可逆，不代表控制点来自真实地面测量。

候选 preset 通过后，再显式替换 `data/tests/calibration_presets.json`，然后运行：

```bash
.venv/bin/python backend/scripts/validate_calibration_presets.py \
  --input data/tests/calibration_presets.json \
  --output-dir data/outputs/calibration_validation \
  --required-clips 028_red_light_static_0008s_30s.mp4
```

导出后必须再运行 `validate_calibration_presets.py`，不要跳过质量校验。
