import type { CumulativeStats, FrameReport } from "../types/frameReport";
import { formatSpeed } from "../utils/formatters";

interface HistoricalAnalysisProps {
  cumulative: CumulativeStats | null;
  history: FrameReport[];
}

export function HistoricalAnalysis({ cumulative, history }: HistoricalAnalysisProps) {
  const firstValidSpeed = (report: FrameReport) =>
    report.active_tracks.find((track) => track.physics_valid && track.speed_kmh !== null)
      ?.speed_kmh ?? null;

  return (
    <section className="panel page-panel">
      <div className="panel-heading">
        <h2>历史数据分析</h2>
      </div>
      <div className="history-summary">
        <strong>{cumulative?.total_frames ?? "N/A"}</strong>
        <span>处理帧</span>
        <strong>{cumulative?.total_unique_tracks ?? "N/A"}</strong>
        <span>唯一轨迹</span>
        <strong>{formatSpeed(cumulative?.avg_speed_kmh ?? null)}</strong>
        <span>平均速度</span>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>帧</th>
            <th>目标</th>
            <th>进入</th>
            <th>离开</th>
            <th>速度</th>
          </tr>
        </thead>
        <tbody>
          {history.length === 0 ? (
            <tr>
              <td colSpan={5}>等待真实分析数据</td>
            </tr>
          ) : (
            history.map((report, index) => (
              <tr key={`${report.frame_index}-${report.timestamp_sec}-${index}`}>
                <td>{report.frame_index}</td>
                <td>{report.active_tracks.length}</td>
                <td>{report.total_in}</td>
                <td>{report.total_out}</td>
                <td>{formatSpeed(firstValidSpeed(report))}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </section>
  );
}
