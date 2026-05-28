import { useState } from "react";

import { FlowChart } from "../components/charts/FlowChart";
import { MetricTile } from "../components/cards/MetricTile";
import { ZoneStatsList } from "../components/cards/ZoneStatsList";
import { VideoPanel } from "../components/video/VideoPanel";
import type { FrameReport } from "../types/frameReport";
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
  report: FrameReport;
  isTaskLoading: boolean;
  onStartTask: (file?: File) => void;
  onStopTask: () => void;
  task: ProcessingTask | null;
}

export function RealtimeMonitor({
  report,
  isTaskLoading,
  onStartTask,
  onStopTask,
  task
}: RealtimeMonitorProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const leadTrack = report.active_tracks[0];
  const avgSpeed = leadTrack?.speed_kmh ?? null;
  const sourceLabel = task?.uploaded_filename ?? task?.source ?? "等待启动 demo://traffic";

  return (
    <div className="screen-grid">
      <VideoPanel tracks={report.active_tracks} />
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
        <p className="file-hint">{selectedFile ? selectedFile.name : "未选择文件时使用模拟交通流"}</p>
        <div className="button-row">
          <button
            className="primary-button"
            disabled={isTaskLoading}
            onClick={() => onStartTask(selectedFile ?? undefined)}
            type="button"
          >
            {selectedFile ? "上传并分析" : "开始演示"}
          </button>
          <button className="secondary-button" disabled={!task || isTaskLoading} onClick={onStopTask} type="button">
            停止
          </button>
        </div>
        <p className="task-status">
          {task ? `${task.status} · ${task.frame_count} 帧 · ${sourceLabel}` : sourceLabel}
        </p>
      </section>
      <div className="metric-grid">
        <MetricTile label="进入" tone="green" value={formatCount(report.total_in)} />
        <MetricTile label="离开" tone="blue" value={formatCount(report.total_out)} />
        <MetricTile label="FPS" value={report.fps.toFixed(1)} />
        <MetricTile label="速度" value={formatSpeed(avgSpeed)} />
        <MetricTile label="置信度" value={formatPercent(leadTrack?.speed_confidence)} />
        <MetricTile label="速度误差" value={formatUncertainty(leadTrack?.speed_uncertainty_kmh)} />
        <MetricTile label="速度区间" value={formatSpeedInterval(leadTrack?.speed_confidence_interval_kmh)} />
        <MetricTile label="区域人数" value={formatCount(report.regional_people_count?.people_count ?? 0)} />
        <MetricTile label="标定质量" value={report.calibration_quality ?? "N/A"} />
        <MetricTile label="安全风险" value={report.safety_metrics?.risk_level ?? "N/A"} />
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
      <section className="panel semantic-panel">
        <div className="panel-heading">
          <h2>风险与上下文</h2>
        </div>
        <div className="semantic-list">
          <div>
            <span>最小跟车时距</span>
            <strong>{formatSeconds(report.safety_metrics?.min_time_headway_sec)}</strong>
          </div>
          <div>
            <span>近似碰撞时距</span>
            <strong>{formatSeconds(report.safety_metrics?.min_time_to_collision_sec)}</strong>
          </div>
          <div>
            <span>交通灯数量</span>
            <strong>{formatCount(report.infrastructure_semantics?.traffic_light_count ?? 0)}</strong>
          </div>
          <div>
            <span>信号灯状态</span>
            <strong>{report.infrastructure_semantics?.traffic_light_state ?? "unknown"}</strong>
          </div>
          <div>
            <span>行人统计模型</span>
            <strong>{report.regional_people_count?.estimation_method ?? "N/A"}</strong>
          </div>
          <div>
            <span>拥堵状态</span>
            <strong>{report.traffic_flow?.congestion_level ?? "N/A"}</strong>
          </div>
        </div>
      </section>
      <ZoneStatsList zones={report.zone_stats} />
      <FlowChart report={report} />
    </div>
  );
}
