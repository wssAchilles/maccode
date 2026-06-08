import { animate, stagger } from "animejs";
import { useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Bot,
  Code2,
  FileVideo,
  ShieldAlert,
  Square,
  UploadCloud,
  X
} from "lucide-react";

import { LLMReportViewer } from "../components/ai/LLMReportViewer";
import { FlowChart } from "../components/charts/FlowChart";
import { MetricTile } from "../components/cards/MetricTile";
import { ZoneStatsList } from "../components/cards/ZoneStatsList";
import { VideoPanel, type VideoPlaybackSnapshot } from "../components/video/VideoPanel";
import { useAIReport } from "../hooks/useAIReport";
import { useAnimeScope } from "../hooks/useAnimeScope";
import type { FrameReport, Track } from "../types/frameReport";
import type { ProcessingTask } from "../types/videoTask";
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
  onResetAnalysis: () => void;
  onStartTask: (file: File) => Promise<ProcessingTask | null>;
  onStopTask: () => void;
  task: ProcessingTask | null;
  taskError: string | null;
}

type AnalysisUiState = "idle" | "selected" | "analyzing" | "complete" | "stopped";

const STATIC_CONTEXT_CLASS_IDS = new Set([9, 10, 11]);
const INITIAL_PLAYBACK_SNAPSHOT: VideoPlaybackSnapshot = {
  currentTimeSec: 0,
  durationSec: 0,
  isPlaying: false
};
const VIDEO_FILE_INPUT_ID = "realtime-video-file-input";

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

function normalizeStatus(value: string | null | undefined) {
  return (value ?? "").trim().toUpperCase();
}

function isElevatedRisk(value: string | null | undefined) {
  const status = normalizeStatus(value);
  return ["CRITICAL", "HIGH", "DANGER", "SEVERE", "ALERT", "RISK"].some((token) =>
    status.includes(token)
  );
}

function isCrowdAlert(value: string | null | undefined) {
  const status = normalizeStatus(value);
  return ["CRITICAL", "HIGH", "DENSE", "CROWDED", "CONGESTED"].some((token) =>
    status.includes(token)
  );
}

function formatDensity(value: number | null | undefined) {
  return finiteNumber(value) ? `${value.toFixed(2)} 人/m²` : "N/A";
}

function formatTrafficDensity(value: number | null | undefined) {
  return finiteNumber(value) ? `${value.toFixed(1)} veh/km` : "N/A";
}

function formatTrackBox(track: Track | null | undefined) {
  if (!track?.xyxy) {
    return "bbox N/A";
  }
  const [x1, y1, x2, y2] = track.xyxy;
  return `bbox ${x1.toFixed(0)},${y1.toFixed(0)}-${x2.toFixed(0)},${y2.toFixed(0)}`;
}

function formatPoint2(value: number[] | [number, number] | null | undefined) {
  if (!Array.isArray(value) || value.length < 2) {
    return "N/A";
  }
  const [x, y] = value;
  return finiteNumber(x) && finiteNumber(y) ? `${x.toFixed(2)}, ${y.toFixed(2)} m` : "N/A";
}

function dominantContactPhase(track: Track | null | undefined) {
  const phases = track?.contact_phase_probabilities;
  if (!phases) {
    return "N/A";
  }
  return Object.entries(phases).sort((left, right) => right[1] - left[1])[0]?.[0] ?? "N/A";
}

function formatDriftMetric(track: Track | null | undefined, key: string) {
  const value = track?.near_far_speed_drift_metrics?.[key];
  return finiteNumber(value) ? value.toFixed(2) : "N/A";
}

function formatScalar(value: number | null | undefined, suffix = "") {
  return finiteNumber(value) ? `${value.toFixed(2)}${suffix}` : "N/A";
}

function identitySwitchProbability(track: Track | null | undefined) {
  const value = track?.identity_posterior?.id_switch_probability;
  return typeof value === "number" ? value : null;
}

function trackGeometryLabel(track: Track | null | undefined) {
  if (!track) {
    return "N/A";
  }
  const plane = track.plane_id ? `plane ${track.plane_id}` : "plane N/A";
  const contact = track.contact_source ? `contact ${track.contact_source}` : "contact N/A";
  const contactState = track.contact_state ? `state ${track.contact_state}` : "state N/A";
  return `${formatTrackBox(track)} · ${plane} · ${contact} · ${contactState}`;
}

function posteriorRiskLabel(track: Track | null | undefined) {
  const risk = track?.joint_physics_posterior?.primary_risk_source;
  return typeof risk === "string" && risk.length > 0 ? risk : "N/A";
}

function posteriorSpeedInterval(track: Track | null | undefined) {
  const interval = track?.joint_physics_posterior?.speed_p05_p50_p95_kmh;
  if (!Array.isArray(interval) || interval.length !== 3) {
    return "N/A";
  }
  const [p05, p50, p95] = interval;
  if (!finiteNumber(p05) || !finiteNumber(p50) || !finiteNumber(p95)) {
    return "N/A";
  }
  return `${p05.toFixed(1)} / ${p50.toFixed(1)} / ${p95.toFixed(1)} km/h`;
}

function trackOptionLabel(track: Track) {
  const state = track.physics_valid ? "physics valid" : track.quality_label;
  return `#${track.tracker_id} / ${track.class_name} / ${state} / ${formatTrackBox(track)}`;
}

function reportForPlayback(
  history: FrameReport[],
  fallbackReport: FrameReport | null,
  playbackSnapshot: VideoPlaybackSnapshot,
  shouldSyncToVideo: boolean
) {
  if (!shouldSyncToVideo || history.length === 0) {
    return fallbackReport;
  }
  let closestReport = history[0];
  let closestDelta = Math.abs((history[0]?.timestamp_sec ?? 0) - playbackSnapshot.currentTimeSec);
  for (const candidate of history) {
    const delta = Math.abs((candidate.timestamp_sec ?? 0) - playbackSnapshot.currentTimeSec);
    if (delta < closestDelta) {
      closestReport = candidate;
      closestDelta = delta;
    }
  }
  return closestReport ?? fallbackReport;
}

export function RealtimeMonitor({
  history,
  report,
  isTaskLoading,
  onResetAnalysis,
  onStartTask,
  onStopTask,
  task,
  taskError
}: RealtimeMonitorProps) {
  const decisionColumnRef = useRef<HTMLElement | null>(null);
  const geekLayerRef = useRef<HTMLDivElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [analysisState, setAnalysisState] = useState<AnalysisUiState>("idle");
  const [isGeekModeOpen, setIsGeekModeOpen] = useState(false);
  const [selectedTrackId, setSelectedTrackId] = useState<number | null>(null);
  const [sceneLabel, setSceneLabel] = useState("");
  const [sceneTagText, setSceneTagText] = useState("");
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [playbackSnapshot, setPlaybackSnapshot] = useState<VideoPlaybackSnapshot>(
    INITIAL_PLAYBACK_SNAPSHOT
  );
  const aiReport = useAIReport();
  const processedVideoUrl = task?.processed_video_url ?? null;
  const isAnalyzing = analysisState === "analyzing" || isTaskLoading;
  const isComplete = analysisState === "complete" && Boolean(processedVideoUrl);
  const canUpload = Boolean(selectedFile) && !isAnalyzing && !isComplete;
  const displayedVideoUrl = isComplete ? processedVideoUrl : videoUrl;
  const showAnalysisOverlay = isComplete;
  const activeReport = reportForPlayback(
    history,
    report,
    playbackSnapshot,
    showAnalysisOverlay && Boolean(displayedVideoUrl)
  );
  const leadTrack = chooseLeadTrack(activeReport);
  const selectedTrack =
    activeReport?.active_tracks.find((track) => track.tracker_id === selectedTrackId) ?? leadTrack;
  const selectedTrackIdentity = selectedTrack
    ? `#${selectedTrack.tracker_id} / ${selectedTrack.class_name}`
    : "未锁定目标";
  const selectedTrackGeometry = trackGeometryLabel(selectedTrack);
  const avgSpeed = dashboardSpeed(activeReport);
  const avgConfidence = averageTrackField(activeReport, "speed_confidence");
  const speedInterval = dashboardSpeedInterval(activeReport, leadTrack);
  const speedMetricValue = finiteNumber(avgSpeed)
    ? formatSpeed(avgSpeed)
    : activeReport
      ? "待收敛"
      : "N/A";
  const calibrationDiagnostics = activeReport?.calibration_diagnostics ?? null;
  const regionalPeople = activeReport?.regional_people_count ?? null;
  const infrastructure = activeReport?.infrastructure_semantics ?? null;
  const safetyMetrics = activeReport?.safety_metrics ?? null;
  const densityValue = regionalPeople?.density_people_per_sqm;
  const densityAlert =
    (finiteNumber(densityValue) && densityValue > 300) || isCrowdAlert(regionalPeople?.crowding_level);
  const riskAlert = isElevatedRisk(safetyMetrics?.risk_level);
  const redLightRiskCount = activeReport
    ? safetyMetrics?.red_light_violation_track_ids?.length ?? 0
    : null;
  const speedingRiskCount = activeReport ? safetyMetrics?.speeding_track_ids?.length ?? 0 : null;
  const hasLiveAlert =
    riskAlert ||
    densityAlert ||
    Boolean(redLightRiskCount && redLightRiskCount > 0) ||
    Boolean(speedingRiskCount && speedingRiskCount > 0);
  const alertEvents = [
    ...(riskAlert ? [`安全态势进入 ${safetyMetrics?.risk_level}，需要优先查看处置建议。`] : []),
    ...(densityAlert ? [`人群密度 ${formatDensity(densityValue)}，已触发密度阈值关注。`] : []),
    ...(redLightRiskCount && redLightRiskCount > 0
      ? [`红灯风险目标 ${redLightRiskCount} 个，AI 报告需同步解释证据链。`]
      : []),
    ...(speedingRiskCount && speedingRiskCount > 0
      ? [`超速目标 ${speedingRiskCount} 个，建议核对标定置信度。`]
      : [])
  ];
  const sourceLabel = selectedFile?.name ?? task?.uploaded_filename ?? task?.source ?? "等待选择 MP4";
  const analysisLabel = !task
    ? selectedFile
      ? "已选择原始视频，点击上传并分析后开始本地 CV 与数学建模"
      : "尚未开始分析"
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
  const uploadButtonLabel = isAnalyzing
    ? "正在分析中"
    : isComplete
      ? "分析完成"
      : "上传并分析";
  const taskStatusText = isAnalyzing
    ? `正在分析 · ${sourceLabel}`
    : isComplete
      ? `分析完成 · ${task?.frame_count ?? 0} 帧 · ${sourceLabel}`
      : analysisState === "stopped"
        ? `已停止 · ${sourceLabel}`
        : sourceLabel;
  const alertEventSignature = alertEvents.join("|");

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
    if (task?.processed_video_url && selectedFile && !isTaskLoading && analysisState === "analyzing") {
      setAnalysisState("complete");
    }
  }, [analysisState, isTaskLoading, selectedFile, task?.processed_video_url]);

  useEffect(() => {
    const tracks = activeReport?.active_tracks ?? [];
    if (tracks.length === 0) {
      setSelectedTrackId(null);
      return;
    }
    if (selectedTrackId !== null && tracks.some((track) => track.tracker_id === selectedTrackId)) {
      return;
    }
    setSelectedTrackId((chooseLeadTrack(activeReport) ?? tracks[0]).tracker_id);
  }, [activeReport, selectedTrackId]);

  useAnimeScope(
    decisionColumnRef,
    () => {
      const alertItems = decisionColumnRef.current?.querySelectorAll<HTMLElement>(".alert-feed p");
      if (!alertItems || alertItems.length === 0) {
        return;
      }
      animate(Array.from(alertItems), {
        opacity: [0, 1],
        y: [5, 0],
        delay: stagger(24),
        duration: 260,
        ease: "out(3)"
      });
    },
    [alertEventSignature, hasLiveAlert]
  );

  useAnimeScope(
    geekLayerRef,
    () => {
      const layer = geekLayerRef.current;
      const drawer = layer?.querySelector<HTMLElement>(".geek-drawer");
      const sections = layer?.querySelectorAll<HTMLElement>(".geek-section, .geek-drawer > .panel");

      if (layer) {
        animate(layer, {
          opacity: [0, 1],
          duration: 180,
          ease: "out(2)"
        });
      }
      if (drawer) {
        animate(drawer, {
          opacity: [0, 1],
          x: [36, 0],
          duration: 320,
          ease: "out(3)"
        });
      }
      if (sections && sections.length > 0) {
        animate(Array.from(sections), {
          opacity: [0, 1],
          y: [8, 0],
          delay: stagger(35, { start: 90 }),
          duration: 260,
          ease: "out(3)"
        });
      }
    },
    [isGeekModeOpen]
  );

  function chooseFile(file: File | null | undefined) {
    if (!file) {
      return;
    }
    onResetAnalysis();
    setSelectedFile(file);
    setPlaybackSnapshot(INITIAL_PLAYBACK_SNAPSHOT);
    setAnalysisState("selected");
  }

  async function startAnalysis() {
    if (!selectedFile || !canUpload) {
      return;
    }
    setAnalysisState("analyzing");
    const nextTask = await onStartTask(selectedFile);
    if (nextTask?.processed_video_url) {
      setAnalysisState("complete");
      return;
    }
    setAnalysisState((current) => (current === "analyzing" ? "selected" : current));
  }

  function stopAnalysis() {
    onStopTask();
    setAnalysisState(selectedFile ? "stopped" : "idle");
  }

  return (
    <div className="screen-grid">
      <main className="realtime-visual-column">
        <section className="video-stage">
          <VideoPanel
            calibrationQuality={showAnalysisOverlay ? activeReport?.calibration_quality ?? null : null}
            homographyGrid={showAnalysisOverlay ? activeReport?.homography_grid ?? null : null}
            onPlaybackSnapshot={setPlaybackSnapshot}
            renderedByBackend={showAnalysisOverlay}
            safetyMetrics={showAnalysisOverlay ? activeReport?.safety_metrics ?? null : null}
            selectedTrackId={showAnalysisOverlay ? selectedTrack?.tracker_id ?? null : null}
            tracks={showAnalysisOverlay ? activeReport?.active_tracks ?? [] : []}
            videoUrl={displayedVideoUrl}
          />
          <div className="video-stage-toolbar">
            <span className={hasLiveAlert ? "live-badge alert" : "live-badge"}>
              <Activity size={15} />
              {hasLiveAlert ? "告警态" : "监控中"}
            </span>
            <button
              aria-expanded={isGeekModeOpen}
              className="geek-toggle"
              onClick={() => setIsGeekModeOpen(true)}
              type="button"
            >
              <Code2 size={16} />
              <span>Geek Mode</span>
            </button>
          </div>
        </section>

        <FlowChart className="flow-panel" history={history} report={activeReport} />

        <section className="panel kpi-panel">
          <div className="panel-heading compact-heading">
            <h2>核心指标库</h2>
            {hasLiveAlert && <AlertTriangle size={18} />}
          </div>
          <div className="metric-grid">
            <MetricTile detail="过线累计" label="进入" tone="green" value={formatCount(activeReport?.total_in)} />
            <MetricTile detail="过线累计" label="离开" tone="blue" value={formatCount(activeReport?.total_out)} />
            <MetricTile
              detail={speedInterval ? formatSpeedInterval(speedInterval) : "空间均值"}
              label="平均时速"
              tone="cyan"
              value={speedMetricValue}
            />
            <MetricTile
              alert={densityAlert}
              detail={regionalPeople?.crowding_level ?? "区域占用"}
              label="人群密度"
              tone={densityAlert ? "red" : "amber"}
              value={formatDensity(densityValue)}
            />
            <MetricTile
              alert={riskAlert || Boolean(redLightRiskCount && redLightRiskCount > 0)}
              detail={`红灯 ${formatCount(redLightRiskCount)} / 超速 ${formatCount(speedingRiskCount)}`}
              label="安全风险"
              tone={riskAlert ? "red" : "neutral"}
              value={safetyMetrics?.risk_level ?? "N/A"}
            />
            <MetricTile
              alert={calibrationDowngraded}
              detail={formatPercent(avgConfidence)}
              label="标定质量"
              tone={calibrationDowngraded ? "amber" : "green"}
              value={activeReport?.calibration_quality ?? "N/A"}
            />
          </div>
        </section>
      </main>

      <aside className="realtime-decision-column" ref={decisionColumnRef}>
        <section className="panel controls-panel command-dock">
          <div className="panel-heading compact-heading">
            <h2>任务控制台</h2>
            <FileVideo size={18} />
          </div>
          <div className="file-control">
            <span>本地视频</span>
            <div className="local-file-picker">
              <input
                accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska,video/webm"
                className="visually-hidden-file"
                id={VIDEO_FILE_INPUT_ID}
                onChange={(event) => {
                  chooseFile(event.target.files?.[0]);
                  event.currentTarget.value = "";
                }}
                type="file"
              />
              <label
                className="file-picker-button"
                htmlFor={VIDEO_FILE_INPUT_ID}
              >
                {selectedFile ? "重新选择" : "选择文件"}
              </label>
              <strong className="file-picker-name">
                {selectedFile ? selectedFile.name : "未选择文件"}
              </strong>
            </div>
          </div>
          <div className="button-row">
            <button
              className={isAnalyzing ? "primary-button loading-button" : "primary-button"}
              disabled={!canUpload}
              onClick={() => void startAnalysis()}
              type="button"
            >
              {isAnalyzing ? <span className="button-spinner" /> : <UploadCloud size={17} />}
              <span>{uploadButtonLabel}</span>
            </button>
            <button
              className="secondary-button"
              disabled={!isAnalyzing}
              onClick={stopAnalysis}
              type="button"
            >
              <Square size={14} />
              <span>停止</span>
            </button>
          </div>
          <p className="task-status">{taskStatusText}</p>
          {(task?.analysis_status === "fallback_demo" || calibrationDowngraded) && (
            <p className="task-warning">{analysisLabel}</p>
          )}
          {task?.analysis_device && <p className="task-status">{`本地推理设备 · ${task.analysis_device}`}</p>}
          {calibrationDiagnostics?.camera_profile_display_name && (
            <p className="task-status">{`机位 Profile · ${calibrationDiagnostics.camera_profile_display_name}`}</p>
          )}
          {processedVideoUrl && <p className="task-status">后端已生成处理视频 MP4</p>}
          {task?.analysis_error && <p className="task-error">真实分析失败：{task.analysis_error}</p>}
          {taskError && <p className="task-error">任务请求失败：{taskError}</p>}
        </section>

        <section className="panel ai-command-panel decision-report-panel">
          <div className="panel-heading">
            <h2>AI 警长报告</h2>
            <button
              className="primary-button"
              disabled={!activeReport || aiReport.isLoading}
              onClick={() =>
                activeReport
                  ? void aiReport.run(activeReport, {
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
                placeholder="学校门口 / 医院门口 / 十字路口"
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
          <div className={hasLiveAlert ? "alert-feed active" : "alert-feed"} aria-live="polite">
            <div>
              {hasLiveAlert ? <ShieldAlert size={16} /> : <Activity size={16} />}
              <strong>{hasLiveAlert ? "实时事件日志" : "实时事件日志"}</strong>
            </div>
            {alertEvents.length > 0 ? (
              alertEvents.map((event) => <p key={event}>{event}</p>)
            ) : (
              <p>当前 FrameReport 未触发高优先级处置事件。</p>
            )}
          </div>
          {aiReport.error && <p className="task-error">AI 报告生成失败：{aiReport.error}</p>}
          <LLMReportViewer
            className="command-report"
            emptyText="等待当前帧研判。"
            isLoading={aiReport.isLoading}
            isTyping={aiReport.isTyping}
            loadingText="正在读取 FrameReport、标定诊断、交通流和风险事件..."
            markdown={aiReport.displayedMarkdown}
          />
        </section>

      </aside>

      {isGeekModeOpen && (
        <div
          className="geek-drawer-layer"
          onClick={() => setIsGeekModeOpen(false)}
          ref={geekLayerRef}
          role="presentation"
        >
          <aside
            aria-labelledby="geek-drawer-title"
            aria-modal="true"
            className="geek-drawer"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
          >
            <div className="geek-drawer-header">
              <div>
                <span>物理底座数据</span>
                <h2 id="geek-drawer-title">Geek Mode</h2>
              </div>
              <button
                aria-label="关闭 Geek Mode"
                className="geek-close-button"
                onClick={() => setIsGeekModeOpen(false)}
                type="button"
              >
                <X size={18} />
              </button>
            </div>

            <section className="geek-section">
              <div className="panel-heading compact-heading">
                <h3>物理语义</h3>
              </div>
              <div className="geek-target-bar">
                <label>
                  <span>当前目标</span>
                  <select
                    disabled={!activeReport?.active_tracks.length}
                    onChange={(event) => setSelectedTrackId(Number(event.target.value))}
                    value={selectedTrack?.tracker_id ?? ""}
                  >
                    {(activeReport?.active_tracks ?? []).map((track) => (
                      <option key={track.tracker_id} value={track.tracker_id}>
                        {trackOptionLabel(track)}
                      </option>
                    ))}
                  </select>
                </label>
                <div>
                  <span>画面对应</span>
                  <strong>{selectedTrackIdentity}</strong>
                  <small>
                    {selectedTrack ? `视频内嵌绿色标签 #${selectedTrack.tracker_id}` : "视频标签 N/A"}
                  </small>
                  <small>{selectedTrackGeometry}</small>
                  <small>
                    {activeReport
                      ? `frame ${activeReport.frame_index} · t=${formatSeconds(activeReport.timestamp_sec)}`
                      : "frame N/A"}
                  </small>
                </div>
              </div>
              <div className="physics-grid">
                <div>
                  <span>Track ID</span>
                  <strong>{selectedTrack ? `#${selectedTrack.tracker_id}` : "N/A"}</strong>
                </div>
                <div>
                  <span>目标类别</span>
                  <strong>{selectedTrack?.class_name ?? "N/A"}</strong>
                </div>
                <div>
                  <span>地面坐标 X</span>
                  <strong>{formatMeters(selectedTrack?.ground_x_m)}</strong>
                </div>
                <div>
                  <span>地面坐标 Y</span>
                  <strong>{formatMeters(selectedTrack?.ground_y_m)}</strong>
                </div>
                <div>
                  <span>速度向量 X</span>
                  <strong>{formatMetersPerSecond(selectedTrack?.velocity_x_mps)}</strong>
                </div>
                <div>
                  <span>速度向量 Y</span>
                  <strong>{formatMetersPerSecond(selectedTrack?.velocity_y_mps)}</strong>
                </div>
                <div>
                  <span>航向角</span>
                  <strong>{formatDegrees(selectedTrack?.heading_deg)}</strong>
                </div>
                <div>
                  <span>加速度</span>
                  <strong>{formatAcceleration(selectedTrack?.acceleration_mps2)}</strong>
                </div>
                <div>
                  <span>速度误差</span>
                  <strong>{formatUncertainty(selectedTrack?.speed_uncertainty_kmh)}</strong>
                </div>
                <div>
                  <span>速度区间</span>
                  <strong>{formatSpeedInterval(selectedTrack?.speed_confidence_interval_kmh)}</strong>
                </div>
                <div>
                  <span>物理总置信度</span>
                  <strong>{formatPercent(selectedTrack?.physics_confidence)}</strong>
                </div>
                <div>
                  <span>速度估计置信度</span>
                  <strong>{formatPercent(selectedTrack?.speed_confidence)}</strong>
                </div>
                <div>
                  <span>速度时序稳定性</span>
                  <strong>{formatPercent(selectedTrack?.speed_stability_score)}</strong>
                </div>
                <div>
                  <span>速度波动系数</span>
                  <strong>{formatPercent(selectedTrack?.speed_cv)}</strong>
                </div>
                <div>
                  <span>最大速度跳变</span>
                  <strong>{formatSpeed(selectedTrack?.max_speed_jump_kmh ?? null)}</strong>
                </div>
                <div>
                  <span>稳定性标签</span>
                  <strong>{selectedTrack?.stability_label ?? "N/A"}</strong>
                </div>
                <div>
                  <span>物理有效性</span>
                  <strong>{selectedTrack ? (selectedTrack.physics_valid ? "valid" : selectedTrack.quality_label) : "N/A"}</strong>
                </div>
                <div>
                  <span>接触状态</span>
                  <strong>{selectedTrack?.contact_state ?? "N/A"}</strong>
                </div>
                <div>
                  <span>接触相位</span>
                  <strong>{dominantContactPhase(selectedTrack)}</strong>
                </div>
                <div>
                  <span>测量策略</span>
                  <strong>{selectedTrack?.measurement_policy ?? "N/A"}</strong>
                </div>
                <div>
                  <span>速度主观测</span>
                  <strong>{formatPoint2(selectedTrack?.body_ground_projection)}</strong>
                </div>
                <div>
                  <span>支撑脚锚点</span>
                  <strong>{formatPoint2(selectedTrack?.support_contact_anchor)}</strong>
                </div>
                <div>
                  <span>脚滑/几何风险</span>
                  <strong>{formatPercent(selectedTrack?.foot_skate_risk)}</strong>
                </div>
                <div>
                  <span>几何状态</span>
                  <strong>{selectedTrack?.geometry_status ?? "N/A"}</strong>
                </div>
                <div>
                  <span>Body 速度</span>
                  <strong>{formatSpeed(selectedTrack?.speed_body_kmh ?? null)}</strong>
                </div>
                <div>
                  <span>步态周期速度</span>
                  <strong>{formatSpeed(selectedTrack?.speed_periodic_kmh ?? null)}</strong>
                </div>
                <div>
                  <span>支撑脚零速残差</span>
                  <strong>
                    {formatScalar(selectedTrack?.support_zero_velocity_residual_mps, " m/s")}
                  </strong>
                </div>
                <div>
                  <span>Body/周期差值</span>
                  <strong>{formatSpeed(selectedTrack?.body_periodic_speed_gap_kmh ?? null)}</strong>
                </div>
                <div>
                  <span>近远漂移分数</span>
                  <strong>{formatScalar(selectedTrack?.near_far_speed_drift_score)}</strong>
                </div>
                <div>
                  <span>Body/周期一致性</span>
                  <strong>{formatPercent(selectedTrack?.body_periodic_consistency)}</strong>
                </div>
                <div>
                  <span>步幅一致性</span>
                  <strong>{formatPercent(selectedTrack?.stride_consistency_score)}</strong>
                </div>
                <div>
                  <span>支撑脚 p95 残差</span>
                  <strong>{formatScalar(selectedTrack?.support_zero_velocity_p95_mps, " m/s")}</strong>
                </div>
                <div>
                  <span>ID 切换概率</span>
                  <strong>{formatPercent(identitySwitchProbability(selectedTrack))}</strong>
                </div>
                <div>
                  <span>度量几何 Gate</span>
                  <strong>{selectedTrack?.metric_geometry_gate_reason ?? "pass"}</strong>
                </div>
                <div>
                  <span>接触 Episode</span>
                  <strong>{formatCount(selectedTrack?.contact_episodes?.length)}</strong>
                </div>
                <div>
                  <span>H 坐标系</span>
                  <strong>{calibrationDiagnostics?.homography_coordinate_space ?? "N/A"}</strong>
                </div>
                <div>
                  <span>点坐标系</span>
                  <strong>{calibrationDiagnostics?.point_coordinate_space ?? "N/A"}</strong>
                </div>
                <div>
                  <span>坐标 Gate</span>
                  <strong>{calibrationDiagnostics?.coordinate_space_gate_reason ?? "pass"}</strong>
                </div>
                <div>
                  <span>畸变一致性</span>
                  <strong>
                    {calibrationDiagnostics?.undistorted_metric_profile
                      ? "undistorted metric"
                      : calibrationDiagnostics?.coordinate_space_warning ?? "raw/unchecked"}
                  </strong>
                </div>
                <div>
                  <span>Pinhole 一致性</span>
                  <strong>{calibrationDiagnostics?.intrinsics_consistency_status ?? "N/A"}</strong>
                </div>
                <div>
                  <span>H 分解残差</span>
                  <strong>
                    {formatScalar(calibrationDiagnostics?.homography_decomposition_residual)}
                  </strong>
                </div>
                <div>
                  <span>Jacobian p95</span>
                  <strong>
                    {formatScalar(
                      calibrationDiagnostics?.local_jacobian_speed_amplification_p95
                    )}
                  </strong>
                </div>
              </div>
            </section>

            <section className="geek-section">
              <div className="panel-heading compact-heading">
                <h3>置信度分解</h3>
              </div>
              <div className="physics-grid">
                <div>
                  <span>标定置信度</span>
                  <strong>{formatPercent(selectedTrack?.calibration_confidence)}</strong>
                </div>
                <div>
                  <span>脚点置信度</span>
                  <strong>{formatPercent(selectedTrack?.contact_confidence)}</strong>
                </div>
                <div>
                  <span>跟踪置信度</span>
                  <strong>{formatPercent(selectedTrack?.tracking_confidence)}</strong>
                </div>
                <div>
                  <span>遮挡置信度</span>
                  <strong>{formatPercent(selectedTrack?.occlusion_confidence)}</strong>
                </div>
                <div>
                  <span>动力学置信度</span>
                  <strong>{formatPercent(selectedTrack?.dynamics_confidence)}</strong>
                </div>
                <div>
                  <span>主要风险因子</span>
                  <strong>{selectedTrack?.confidence_rejection_reason ?? "N/A"}</strong>
                </div>
                <div>
                  <span>后验主风险</span>
                  <strong>{posteriorRiskLabel(selectedTrack)}</strong>
                </div>
                <div>
                  <span>后验速度 p05/p50/p95</span>
                  <strong>{posteriorSpeedInterval(selectedTrack)}</strong>
                </div>
                <div>
                  <span>主不确定性</span>
                  <strong>{selectedTrack?.dominant_uncertainty_source ?? "N/A"}</strong>
                </div>
                <div>
                  <span>速度-尺度 corr</span>
                  <strong>{formatDriftMetric(selectedTrack, "speed_local_scale_correlation")}</strong>
                </div>
                <div>
                  <span>速度-高度 corr</span>
                  <strong>{formatDriftMetric(selectedTrack, "speed_inverse_height_correlation")}</strong>
                </div>
              </div>
            </section>

            <section className="geek-section">
              <div className="panel-heading compact-heading">
                <h3>风险与上下文</h3>
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
                  <span>交通流密度 k</span>
                  <strong>{formatTrafficDensity(activeReport?.traffic_flow?.density_k_veh_per_km)}</strong>
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
                  <strong>{activeReport?.traffic_flow?.congestion_level ?? "N/A"}</strong>
                </div>
              </div>
            </section>

            <ZoneStatsList report={activeReport} />
          </aside>
        </div>
      )}
    </div>
  );
}
