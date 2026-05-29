import type { FrameReport, Track } from "../../types/frameReport";

interface FlowChartProps {
  history?: FrameReport[];
  report: FrameReport | null;
}

interface FlowBin {
  density: number | null;
  flow: number;
  label: string;
  people: number;
  speed: number | null;
  vehicles: number;
}

interface HeatCell {
  count: number;
  key: string;
  x: number;
  y: number;
}

const STATIC_CONTEXT_CLASS_IDS = new Set([9, 10, 11]);
const HEAT_COLUMNS = 9;
const HEAT_ROWS = 5;

function finiteNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function average(values: number[]) {
  return values.length > 0 ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

function latestReports(report: FrameReport | null, history?: FrameReport[]) {
  const reports = history && history.length > 0 ? history : report ? [report] : [];
  return reports.slice(-72);
}

function dynamicTracks(report: FrameReport) {
  return report.active_tracks.filter((track) => !STATIC_CONTEXT_CLASS_IDS.has(track.class_id));
}

function vehicleCount(report: FrameReport) {
  return (
    report.infrastructure_semantics?.dynamic_vehicle_count ??
    report.active_tracks.filter((track) => [2, 3, 5, 7].includes(track.class_id)).length
  );
}

function peopleCount(report: FrameReport) {
  return (
    report.regional_people_count?.people_count ??
    report.active_tracks.filter((track) => track.class_id === 0).length
  );
}

function buildBins(reports: FrameReport[]) {
  if (reports.length === 0) {
    return [];
  }
  const targetBins = Math.min(8, Math.max(1, reports.length));
  const binSize = Math.ceil(reports.length / targetBins);
  const bins: FlowBin[] = [];
  for (let start = 0; start < reports.length; start += binSize) {
    const chunk = reports.slice(start, start + binSize);
    const flowValues = chunk.map((item) => item.traffic_flow?.flow_q_veh_per_hour ?? 0);
    const speedValues = chunk
      .map((item) => item.traffic_flow?.space_mean_speed_kmh)
      .filter(finiteNumber);
    const densityValues = chunk
      .map((item) => item.traffic_flow?.density_k_veh_per_km)
      .filter(finiteNumber);
    const startSec = chunk[0]?.timestamp_sec ?? 0;
    const endSec = chunk[chunk.length - 1]?.timestamp_sec ?? startSec;
    bins.push({
      density: average(densityValues),
      flow: average(flowValues) ?? 0,
      label: `${startSec.toFixed(0)}-${endSec.toFixed(0)}s`,
      people: Math.max(...chunk.map(peopleCount), 0),
      speed: average(speedValues),
      vehicles: Math.max(...chunk.map(vehicleCount), 0)
    });
  }
  return bins;
}

function buildHeatCells(reports: FrameReport[]) {
  const observedTracks = reports.flatMap(dynamicTracks);
  const worldPoints = observedTracks
    .filter((track) => finiteNumber(track.ground_x_m) && finiteNumber(track.ground_y_m))
    .map((track) => [track.ground_x_m as number, track.ground_y_m as number] as const);
  const xValues = worldPoints.map(([x]) => x);
  const yValues = worldPoints.map(([, y]) => y);
  const minX = Math.min(...xValues, 0);
  const maxX = Math.max(...xValues, 1);
  const minY = Math.min(...yValues, 0);
  const maxY = Math.max(...yValues, 1);
  const cells = new Map<string, HeatCell>();

  for (const [x, y] of worldPoints) {
    const col = Math.min(
      HEAT_COLUMNS - 1,
      Math.max(0, Math.floor(((x - minX) / Math.max(maxX - minX, 1e-6)) * HEAT_COLUMNS))
    );
    const row = Math.min(
      HEAT_ROWS - 1,
      Math.max(0, Math.floor(((y - minY) / Math.max(maxY - minY, 1e-6)) * HEAT_ROWS))
    );
    const key = `${col}:${row}`;
    const previous = cells.get(key);
    cells.set(key, {
      count: (previous?.count ?? 0) + 1,
      key,
      x: col,
      y: row
    });
  }

  return {
    cells: Array.from(cells.values()),
    maxCount: Math.max(...Array.from(cells.values()).map((cell) => cell.count), 1),
    trackCount: observedTracks.length
  };
}

function latestValidSpeed(report: FrameReport | null) {
  const track = report?.active_tracks.find(
    (item: Track) => item.physics_valid && finiteNumber(item.speed_kmh)
  );
  return track?.speed_kmh ?? report?.traffic_flow?.space_mean_speed_kmh ?? null;
}

function formatMetric(value: number | null | undefined, suffix = "") {
  return finiteNumber(value) ? `${value.toFixed(1)}${suffix}` : "待收敛";
}

export function FlowChart({ history, report }: FlowChartProps) {
  const reports = latestReports(report, history);
  if (reports.length === 0) {
    return (
      <section className="panel wide">
        <div className="panel-heading">
          <h2>流量趋势</h2>
        </div>
        <div className="empty-state">等待真实分析数据</div>
      </section>
    );
  }

  const bins = buildBins(reports);
  const currentReport = report ?? reports[reports.length - 1];
  const maxFlow = Math.max(...bins.map((bin) => bin.flow), 1);
  const maxSpeed = Math.max(...bins.map((bin) => bin.speed ?? 0), latestValidSpeed(currentReport) ?? 0, 1);
  const speedPoints = bins
    .map((bin, index) => {
      if (!finiteNumber(bin.speed)) {
        return null;
      }
      const x = 46 + index * (500 / Math.max(bins.length - 1, 1));
      const y = 172 - (bin.speed / maxSpeed) * 118;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .filter((point): point is string => Boolean(point));
  const heat = buildHeatCells(reports);
  const currentPeople = peopleCount(currentReport);
  const currentVehicles = vehicleCount(currentReport);

  return (
    <section className="panel wide">
      <div className="panel-heading">
        <h2>流量趋势</h2>
        <span className="panel-subtitle">q/k/v + 空间热力分布</span>
      </div>
      <div className="flow-dashboard">
        <div className="flow-plot-card">
          <div className="flow-chart-legend">
            <span className="legend-flow">流量 q</span>
            <span className="legend-speed">空间平均速度 v</span>
          </div>
          <svg className="flow-svg" role="img" viewBox="0 0 600 220">
            <line className="axis-line" x1="38" x2="568" y1="180" y2="180" />
            <line className="axis-line" x1="38" x2="38" y1="34" y2="180" />
            {bins.map((bin, index) => {
              const x = 52 + index * (500 / Math.max(bins.length, 1));
              const height = Math.max(10, (bin.flow / maxFlow) * 120);
              return (
                <g key={bin.label}>
                  <rect
                    className="flow-bar"
                    height={height}
                    rx="5"
                    width="28"
                    x={x}
                    y={180 - height}
                  />
                  <text className="flow-axis-label" x={x + 14} y="204">
                    {bin.label}
                  </text>
                </g>
              );
            })}
            {speedPoints.length > 1 && <polyline className="speed-line" points={speedPoints.join(" ")} />}
            {speedPoints.map((point) => {
              const [x, y] = point.split(",");
              return <circle className="speed-point" cx={x} cy={y} key={point} r="4" />;
            })}
          </svg>
        </div>
        <div className="heatmap-card">
          <div>
            <h3>空间占用热力图</h3>
            <p>由目标地面坐标轨迹累积生成，颜色越亮表示该真实区域被占用越频繁。</p>
          </div>
          <div className="heatmap-grid">
            {Array.from({ length: HEAT_ROWS * HEAT_COLUMNS }).map((_, index) => {
              const x = index % HEAT_COLUMNS;
              const y = Math.floor(index / HEAT_COLUMNS);
              const cell = heat.cells.find((item) => item.x === x && item.y === y);
              const intensity = cell ? cell.count / heat.maxCount : 0;
              return (
                <span
                  aria-label={`heat cell ${x}-${y}`}
                  className="heatmap-cell"
                  key={`${x}:${y}`}
                  style={{
                    backgroundColor: `rgba(96, 165, 250, ${0.08 + intensity * 0.72})`
                  }}
                />
              );
            })}
          </div>
        </div>
      </div>
      <div className="flow-metric-row">
        <div>
          <span>当前车辆</span>
          <strong>{currentVehicles}</strong>
        </div>
        <div>
          <span>当前行人</span>
          <strong>{currentPeople}</strong>
        </div>
        <div>
          <span>流量 q</span>
          <strong>{formatMetric(currentReport.traffic_flow?.flow_q_veh_per_hour, " veh/h")}</strong>
        </div>
        <div>
          <span>密度 k</span>
          <strong>{formatMetric(currentReport.traffic_flow?.density_k_veh_per_km, " veh/km")}</strong>
        </div>
        <div>
          <span>速度 v</span>
          <strong>{formatMetric(latestValidSpeed(currentReport), " km/h")}</strong>
        </div>
        <div>
          <span>热力轨迹样本</span>
          <strong>{heat.trackCount}</strong>
        </div>
      </div>
    </section>
  );
}
