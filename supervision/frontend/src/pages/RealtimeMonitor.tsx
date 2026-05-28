import { FlowChart } from "../components/charts/FlowChart";
import { MetricTile } from "../components/cards/MetricTile";
import { ZoneStatsList } from "../components/cards/ZoneStatsList";
import { VideoPanel } from "../components/video/VideoPanel";
import type { FrameReport } from "../types/frameReport";
import type { ProcessingTask } from "../types/videoTask";
import { formatCount, formatSpeed } from "../utils/formatters";

interface RealtimeMonitorProps {
  report: FrameReport;
  isTaskLoading: boolean;
  onStartTask: () => void;
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
  const avgSpeed = report.active_tracks[0]?.speed_kmh ?? null;

  return (
    <div className="screen-grid">
      <VideoPanel tracks={report.active_tracks} />
      <section className="panel controls-panel">
        <div className="panel-heading">
          <h2>处理任务</h2>
        </div>
        <div className="button-row">
          <button className="primary-button" disabled={isTaskLoading} onClick={onStartTask} type="button">
            开始演示
          </button>
          <button className="secondary-button" disabled={!task || isTaskLoading} onClick={onStopTask} type="button">
            停止
          </button>
        </div>
        <p className="task-status">
          {task ? `${task.status} · ${task.frame_count} 帧 · ${task.source}` : "等待启动 demo://traffic"}
        </p>
      </section>
      <div className="metric-grid">
        <MetricTile label="进入" tone="green" value={formatCount(report.total_in)} />
        <MetricTile label="离开" tone="blue" value={formatCount(report.total_out)} />
        <MetricTile label="FPS" value={report.fps.toFixed(1)} />
        <MetricTile label="速度" value={formatSpeed(avgSpeed)} />
      </div>
      <ZoneStatsList zones={report.zone_stats} />
      <FlowChart report={report} />
    </div>
  );
}
