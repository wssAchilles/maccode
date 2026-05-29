import type { FrameReport } from "../../types/frameReport";

interface FlowChartProps {
  report: FrameReport | null;
}

export function FlowChart({ report }: FlowChartProps) {
  if (!report) {
    return (
      <section className="panel wide">
        <div className="panel-heading">
          <h2>流量趋势</h2>
        </div>
        <div className="empty-state">等待真实分析数据</div>
      </section>
    );
  }

  const bars = [report.total_in, report.total_out, report.active_tracks.length, Math.round(report.fps)];
  const max = Math.max(...bars, 1);

  return (
    <section className="panel wide">
      <div className="panel-heading">
        <h2>流量趋势</h2>
      </div>
      <div className="bars">
        {bars.map((value, index) => (
          <div className="bar-column" key={`${value}-${index}`}>
            <div className="bar" style={{ height: `${Math.max(12, (value / max) * 120)}px` }} />
            <span>{value}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
