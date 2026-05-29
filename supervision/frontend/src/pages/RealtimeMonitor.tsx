import { useEffect, useState } from "react";
import { Bot } from "lucide-react";

import { listVideoSamples } from "../api/video";
import { FlowChart } from "../components/charts/FlowChart";
import { MetricTile } from "../components/cards/MetricTile";
import { ZoneStatsList } from "../components/cards/ZoneStatsList";
import { VideoPanel } from "../components/video/VideoPanel";
import { useAIReport } from "../hooks/useAIReport";
import type { FrameReport, Track } from "../types/frameReport";
import type { ProcessingTask, VideoSample } from "../types/videoTask";
import {
  formatAcceleration,
  formatCount,
  formatDegrees,
  formatMeters,
  formatMetersPerSecond,
  formatPercent,
  formatSeconds,
  formatSpeed,
  formatSpeedInterval,
  formatUncertainty
} from "../utils/formatters";

interface RealtimeMonitorProps {
  history: FrameReport[];
  report: FrameReport | null;
  isTaskLoading: boolean;
  onStartSample: (source: string) => void;
  onStartTask: (file: File) => void;
  onStopTask: () => void;
  task: ProcessingTask | null;
  taskError: string | null;
}

const STATIC_CONTEXT_CLASS_IDS = new Set([9, 10, 11]);

function finiteNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function average(values: number[]) {
  return values.length === 0 ? null : values.reduce((sum, value) => sum + value, 0) / values.length;
}

function measuredTracks(report: FrameReport | null) {
  return (report?.active_tracks ?? []).filter(
    (track) => track.physics_valid && finiteNumber(track.speed_kmh)
  );
}

function dynamicTracks(report: FrameReport | null) {
  return (report?.active_tracks ?? []).filter((track) => !STATIC_CONTEXT_CLASS_IDS.has(track.class_id));
}

function chooseLeadTrack(report: FrameReport | null): Track | undefined {
  const tracksWithSpeed = measuredTracks(report);
  if (tracksWithSpeed.length > 0) {
    return [...tracksWithSpeed].sort(
      (left, right) => (right.speed_confidence ?? 0) - (left.speed_confidence ?? 0)
    )[0];
  }
  return dynamicTracks(report)[0];
}

function averageTrackField(report: FrameReport | null, field: "speed_confidence" | "speed_uncertainty_kmh") {
  return average(
    measuredTracks(report)
      .map((track) => track[field])
      .filter(finiteNumber)
  );
}

function dashboardSpeed(report: FrameReport | null) {
  const spaceMeanSpeed = report?.traffic_flow?.space_mean_speed_kmh;
  if (finiteNumber(spaceMeanSpeed)) {
    return spaceMeanSpeed;
  }
  return average(measuredTracks(report).map((track) => track.speed_kmh).filter(finiteNumber));
}

function dashboardSpeedInterval(report: FrameReport | null, leadTrack: Track | undefined) {
  if (leadTrack?.speed_confidence_interval_kmh) {
    return leadTrack.speed_confidence_interval_kmh;
  }
  const band = report?.calibration_diagnostics?.speed_band_kmh;
  if (band && finiteNumber(band[0]) && finiteNumber(band[1])) {
    return [band[0], band[1]] as [number, number];
  }
  const speeds = measuredTracks(report).map((track) => track.speed_kmh).filter(finiteNumber);
  if (speeds.length === 0) {
    return null;
  }
  return [Math.min(...speeds), Math.max(...speeds)] as [number, number];
}

export function RealtimeMonitor({
  history,
  report,
  isTaskLoading,
  onStartSample,
  onStartTask,
  onStopTask,
  task,
  taskError
}: RealtimeMonitorProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedSampleSource, setSelectedSampleSource] = useState("");
  const [sceneLabel, setSceneLabel] = useState("");
  const [sceneTagText, setSceneTagText] = useState("");
  const [samples, setSamples] = useState<VideoSample[]>([]);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const aiReport = useAIReport();
  const leadTrack = chooseLeadTrack(report);
  const avgSpeed = dashboardSpeed(report);
  const avgConfidence = averageTrackField(report, "speed_confidence");
  const avgUncertainty = averageTrackField(report, "speed_uncertainty_kmh");
  const speedInterval = dashboardSpeedInterval(report, leadTrack);
  const speedMetricValue = finiteNumber(avgSpeed)
    ? formatSpeed(avgSpeed)
    : report
      ? "待收敛"
      : "N/A";
  const calibrationDiagnostics = report?.calibration_diagnostics ?? null;
  const autoCalibration = calibrationDiagnostics?.auto_calibration ?? null;
  const homographyGrid = report?.homography_grid ?? null;
  const processedVideoUrl = task?.processed_video_url ?? null;
  const regionalPeople = report?.regional_people_count ?? null;
  const infrastructure = report?.infrastructure_semantics ?? null;
  const safetyMetrics = report?.safety_metrics ?? null;
  const sourceLabel = task?.uploaded_filename ?? task?.source ?? "等待选择 MP4 或真实样片";
  const analysisLabel = !task
    ? "尚未开始分析"
    : task.analysis_status === "real_video"
      ? task.calibration_source === "scene_profile_preset"
        ? "真实视频分析 · scene_profile_preset（未找到该视频 YAML，已降级）"
        : calibrationDiagnostics?.camera_profile_id
          ? `真实视频分析 · 固定机位标定复用 · ${calibrationDiagnostics.camera_profile_id}`
        : `真实视频分析 · ${task.calibration_source ?? "calibration"}`
      : task.analysis_status === "fallback_demo"
        ? "真实视频不可解析，已回退模拟演示"
        : "本地模拟交通流";
  const calibrationDowngraded = task?.calibration_source === "scene_profile_preset";

  useEffect(() => {
    if (!selectedFile) {
      setVideoUrl(null);
      return undefined;
    }
    const url = URL.createObjectURL(selectedFile);
    setVideoUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [selectedFile]);

  useEffect(() => {
    let isMounted = true;
    listVideoSamples()
      .then((nextSamples) => {
        if (isMounted) {
          setSamples(nextSamples);
          setSelectedSampleSource(nextSamples[0]?.source ?? "");
        }
      })
      .catch(() => {
        if (isMounted) {
          setSamples([]);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="screen-grid">
      <VideoPanel
        calibrationQuality={report?.calibration_quality ?? null}
        homographyGrid={report?.homography_grid ?? null}
        renderedByBackend={Boolean(processedVideoUrl)}
        safetyMetrics={report?.safety_metrics ?? null}
        tracks={report?.active_tracks ?? []}
        videoUrl={processedVideoUrl ?? videoUrl}
      />
      <section className="panel controls-panel">
        <div className="panel-heading">
          <h2>处理任务</h2>
        </div>
        <label className="file-control">
          <span>本地视频</span>
          <input
            accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska,video/webm"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            type="file"
          />
        </label>
        <p className="file-hint">{selectedFile ? selectedFile.name : "请选择 MP4，或使用真实样片开始分析"}</p>
        <label className="file-control">
          <span>真实样片</span>
          <select
            disabled={samples.length === 0}
            onChange={(event) => setSelectedSampleSource(event.target.value)}
            value={selectedSampleSource}
          >
            {samples.map((sample) => (
              <option key={sample.source} value={sample.source}>
                {sample.name}
              </option>
            ))}
          </select>
        </label>
        <div className="button-row">
          <button
            className="primary-button"
            disabled={!selectedFile || isTaskLoading}
            onClick={() => selectedFile && onStartTask(selectedFile)}
            type="button"
          >
            上传并分析
          </button>
          <button className="secondary-button" disabled={!task || isTaskLoading} onClick={onStopTask} type="button">
            停止
          </button>
          <button
            className="secondary-button"
            disabled={!selectedSampleSource || isTaskLoading}
            onClick={() => onStartSample(selectedSampleSource)}
            type="button"
          >
            分析真实样片
          </button>
        </div>
        <p className="task-status">
          {task ? `${task.status} · ${task.frame_count} 帧 · ${sourceLabel}` : sourceLabel}
        </p>
        <p className={task?.analysis_status === "fallback_demo" || calibrationDowngraded ? "task-warning" : "task-status"}>
          {analysisLabel}
        </p>
        {task?.analysis_device && <p className="task-status">{`本地推理设备 · ${task.analysis_device}`}</p>}
        {calibrationDiagnostics?.camera_profile_display_name && (
          <p className="task-status">{`机位 Profile · ${calibrationDiagnostics.camera_profile_display_name}`}</p>
        )}
        {processedVideoUrl && <p className="task-status">后端已生成处理视频 MP4</p>}
        {task?.analysis_error && <p className="task-error">真实分析失败：{task.analysis_error}</p>}
        {taskError && <p className="task-error">任务请求失败：{taskError}</p>}
      </section>
      <section className="panel ai-command-panel">
        <div className="panel-heading">
          <h2>AI 警长报告</h2>
          <button
            className="primary-button"
            disabled={!report || aiReport.isLoading}
            onClick={() =>
              report
                ? void aiReport.run(report, {
                    location_label: sceneLabel || undefined,
                    scene_tags: sceneTagText
                      .split(/[,，\s]+/)
                      .map((tag) => tag.trim())
                      .filter(Boolean)
                  })
                : undefined
            }
            type="button"
          >
            <Bot size={18} />
            <span>{aiReport.isLoading ? "生成中" : "生成处置报告"}</span>
          </button>
        </div>
        <div className="ai-context-controls">
          <label>
            <span>场景标签</span>
            <input
              onChange={(event) => setSceneLabel(event.target.value)}
              placeholder="如：学校门口 / 医院门口 / 十字路口"
              value={sceneLabel}
            />
          </label>
          <label>
            <span>上下文 tags</span>
            <input
              onChange={(event) => setSceneTagText(event.target.value)}
              placeholder="traffic, rain, school_zone"
              value={sceneTagText}
            />
          </label>
        </div>
        {aiReport.error && <p className="task-error">AI 报告生成失败：{aiReport.error}</p>}
        <article className={aiReport.displayedMarkdown ? "command-report" : "command-report empty"}>
          {aiReport.displayedMarkdown ? (
            <>
              {aiReport.displayedMarkdown}
              {aiReport.isTyping && <span className="typing-cursor" />}
            </>
          ) : aiReport.isLoading ? (
            "正在读取当前 FrameReport、标定诊断、交通流和风险事件..."
          ) : (
            "等待生成。报告将基于当前后端 FrameReport 与数学上下文生成。"
          )}
        </article>
      </section>
      <div className="metric-grid">
        <MetricTile label="进入" tone="green" value={formatCount(report?.total_in)} />
        <MetricTile label="离开" tone="blue" value={formatCount(report?.total_out)} />
        <MetricTile label="FPS" value={report ? report.fps.toFixed(1) : "N/A"} />
        <MetricTile label="速度" value={speedMetricValue} />
        <MetricTile label="置信度" value={formatPercent(avgConfidence)} />
        <MetricTile label="速度误差" value={formatUncertainty(avgUncertainty)} />
        <MetricTile label="速度区间" value={formatSpeedInterval(speedInterval)} />
        <MetricTile label="区域人数" value={formatCount(regionalPeople?.people_count)} />
        <MetricTile label="标定质量" value={report?.calibration_quality ?? "N/A"} />
        <MetricTile label="安全风险" value={safetyMetrics?.risk_level ?? "N/A"} />
        <MetricTile
          label="人群密度"
          value={
            regionalPeople?.density_people_per_sqm === undefined
              ? "N/A"
              : `${regionalPeople.density_people_per_sqm.toFixed(2)} 人/m²`
          }
        />
        <MetricTile
          label="红灯风险"
          value={formatCount(report ? safetyMetrics?.red_light_violation_track_ids?.length ?? 0 : null)}
        />
      </div>
      <section className="panel physics-panel">
        <div className="panel-heading">
          <h2>物理语义</h2>
        </div>
        <div className="physics-grid">
          <div>
            <span>地面坐标 X</span>
            <strong>{formatMeters(leadTrack?.ground_x_m)}</strong>
          </div>
          <div>
            <span>地面坐标 Y</span>
            <strong>{formatMeters(leadTrack?.ground_y_m)}</strong>
          </div>
          <div>
            <span>速度向量 X</span>
            <strong>{formatMetersPerSecond(leadTrack?.velocity_x_mps)}</strong>
          </div>
          <div>
            <span>速度向量 Y</span>
            <strong>{formatMetersPerSecond(leadTrack?.velocity_y_mps)}</strong>
          </div>
          <div>
            <span>航向角</span>
            <strong>{formatDegrees(leadTrack?.heading_deg)}</strong>
          </div>
          <div>
            <span>加速度</span>
            <strong>{formatAcceleration(leadTrack?.acceleration_mps2)}</strong>
          </div>
        </div>
      </section>
      <section className="panel math-panel">
        <div className="panel-heading">
          <h2>数学建模证据</h2>
        </div>
        <div className="physics-grid">
          <div>
            <span>机位 Profile</span>
            <strong>{calibrationDiagnostics?.camera_profile_id ?? "N/A"}</strong>
          </div>
          <div>
            <span>Profile 角色</span>
            <strong>{calibrationDiagnostics?.camera_profile_role ?? "N/A"}</strong>
          </div>
          <div>
            <span>标定来源</span>
            <strong>{calibrationDiagnostics?.calibration_source ?? "N/A"}</strong>
          </div>
          <div>
            <span>自动标定置信度</span>
            <strong>{formatPercent(autoCalibration?.auto_calibration_confidence)}</strong>
          </div>
          <div>
            <span>自动标定策略</span>
            <strong>{autoCalibration?.selected_strategy ?? "N/A"}</strong>
          </div>
          <div>
            <span>尺度先验</span>
            <strong>{autoCalibration?.scale_prior_used ?? "N/A"}</strong>
          </div>
          <div>
            <span>几何线索来源</span>
            <strong>{autoCalibration?.evidence_sources?.join(" + ") ?? "N/A"}</strong>
          </div>
          <div>
            <span>首帧候选线</span>
            <strong>
              {calibrationDiagnostics?.frame_geometry_evidence?.candidate_line_count ?? "N/A"}
            </strong>
          </div>
          <div>
            <span>候选 H 方法</span>
            <strong>{autoCalibration?.homography_proposal?.method ?? "N/A"}</strong>
          </div>
          <div>
            <span>候选 H RMSE</span>
            <strong>
              {autoCalibration?.homography_proposal
                ? `${autoCalibration.homography_proposal.reprojection_rmse.toFixed(3)} m`
                : "N/A"}
            </strong>
          </div>
          <div>
            <span>单应性模型</span>
            <strong>{calibrationDiagnostics?.homography_model ?? "N/A"}</strong>
          </div>
          <div>
            <span>重投影 RMSE</span>
            <strong>
              {calibrationDiagnostics
                ? `${calibrationDiagnostics.reprojection_rmse_px.toFixed(3)} px`
                : "N/A"}
            </strong>
          </div>
          <div>
            <span>RANSAC 内点</span>
            <strong>{calibrationDiagnostics?.inlier_count ?? "N/A"}</strong>
          </div>
          <div>
            <span>条件数</span>
            <strong>
              {calibrationDiagnostics
                ? calibrationDiagnostics.condition_number.toExponential(2)
                : "N/A"}
            </strong>
          </div>
          <div>
            <span>位置 RMSE</span>
            <strong>{formatMeters(calibrationDiagnostics?.position_rmse_m)}</strong>
          </div>
          <div>
            <span>网格生成</span>
            <strong>{homographyGrid?.generated_from ?? "N/A"}</strong>
          </div>
          <div>
            <span>尺度不确定性</span>
            <strong>
              {calibrationDiagnostics?.scale_uncertainty_pct === undefined
                ? "N/A"
                : `${calibrationDiagnostics.scale_uncertainty_pct.toFixed(1)}%`}
            </strong>
          </div>
        </div>
        <div className="error-source-list">
          {(calibrationDiagnostics?.error_sources ?? []).slice(0, 4).map((source) => (
            <span key={source}>{source}</span>
          ))}
        </div>
      </section>
      <section className="panel semantic-panel">
        <div className="panel-heading">
          <h2>风险与上下文</h2>
        </div>
        <div className="semantic-list">
          <div>
            <span>最小跟车时距</span>
            <strong>{formatSeconds(safetyMetrics?.min_time_headway_sec)}</strong>
          </div>
          <div>
            <span>近似碰撞时距</span>
            <strong>{formatSeconds(safetyMetrics?.min_time_to_collision_sec)}</strong>
          </div>
          <div>
            <span>交通灯数量</span>
            <strong>{formatCount(infrastructure?.traffic_light_count)}</strong>
          </div>
          <div>
            <span>信号灯状态</span>
            <strong>{infrastructure?.traffic_light_state ?? "N/A"}</strong>
          </div>
          <div>
            <span>信号灯来源</span>
            <strong>{infrastructure?.traffic_light_state_source ?? "N/A"}</strong>
          </div>
          <div>
            <span>行人统计模型</span>
            <strong>{regionalPeople?.estimation_method ?? "N/A"}</strong>
          </div>
          <div>
            <span>密度积分人数</span>
            <strong>
              {regionalPeople?.integrated_people_count === undefined
                ? "N/A"
                : regionalPeople.integrated_people_count.toFixed(1)}
            </strong>
          </div>
          <div>
            <span>人群等级</span>
            <strong>{regionalPeople?.crowding_level ?? "N/A"}</strong>
          </div>
          <div>
            <span>红灯候选 ID</span>
            <strong>
              {(infrastructure?.red_light_violation_candidate_track_ids ?? []).join(", ") || "N/A"}
            </strong>
          </div>
          <div>
            <span>规则来源</span>
            <strong>{safetyMetrics?.rule_source ?? "N/A"}</strong>
          </div>
          <div>
            <span>Profile 风险区</span>
            <strong>
              {safetyMetrics?.configured_risk_areas?.length === undefined
                ? "N/A"
                : safetyMetrics.configured_risk_areas.length}
            </strong>
          </div>
          <div>
            <span>信号灯 ROI</span>
            <strong>
              {infrastructure?.configured_traffic_light_rois?.length === undefined
                ? "N/A"
                : infrastructure.configured_traffic_light_rois.length}
            </strong>
          </div>
          <div>
            <span>拥堵状态</span>
            <strong>{report?.traffic_flow?.congestion_level ?? "N/A"}</strong>
          </div>
        </div>
      </section>
      <ZoneStatsList report={report} />
      <FlowChart history={history} report={report} />
    </div>
  );
}
