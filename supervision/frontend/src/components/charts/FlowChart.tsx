import type { FrameReport, Track } from "../../types/frameReport";

interface FlowChartProps {
  className?: string;
  history?: FrameReport[];
  report: FrameReport | null;
}

interface FlowBin {
  axisLabel: string;
  density: number | null;
  flow: number;
  label: string;
  people: number;
  speed: number | null;
  vehicles: number;
}

interface OccupancyBand {
  count: number;
  label: string;
  widthPct: number;
  xPct: number;
}

interface OccupancyPoint {
  key: string;
  intensity: number;
  kind: "person" | "vehicle" | "other";
  xPct: number;
  yPct: number;
}

const STATIC_CONTEXT_CLASS_IDS = new Set([9, 10, 11]);
const OCCUPANCY_BANDS = 4;

function finiteNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function average(values: number[]) {
  return values.length > 0 ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

function formatAxisTimeLabel(value: number, durationSec: number) {
  return durationSec < 10 ? `${value.toFixed(1)}s` : `${value.toFixed(0)}s`;
}

function shouldShowAxisLabel(index: number, total: number) {
  if (total <= 5) {
    return true;
  }
  return index === 0 || index === total - 1 || index === Math.floor((total - 1) / 2);
}

function latestReports(report: FrameReport | null, history?: FrameReport[]) {
  const reports = history && history.length > 0 ? history : report ? [report] : [];
  if (!report) {
    return reports.slice(-72);
  }
  const currentTimeSec = report.timestamp_sec;
  if (!finiteNumber(currentTimeSec)) {
    return reports.slice(-72);
  }
  const reportsUntilCurrentTime = reports.filter(
    (item) => finiteNumber(item.timestamp_sec) && item.timestamp_sec <= currentTimeSec
  );
  if (reportsUntilCurrentTime.length === 0) {
    return [report];
  }
  return reportsUntilCurrentTime.slice(-72);
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
  const firstSec = reports[0]?.timestamp_sec ?? 0;
  const lastSec = reports[reports.length - 1]?.timestamp_sec ?? firstSec;
  const durationSec = Math.max(0, lastSec - firstSec);
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
    const midpointSec = (startSec + endSec) / 2;
    bins.push({
      axisLabel: formatAxisTimeLabel(midpointSec, durationSec),
      density: average(densityValues),
      flow: average(flowValues) ?? 0,
      label:
        durationSec < 10
          ? `${startSec.toFixed(1)}-${endSec.toFixed(1)}s`
          : `${startSec.toFixed(0)}-${endSec.toFixed(0)}s`,
      people: Math.max(...chunk.map(peopleCount), 0),
      speed: average(speedValues),
      vehicles: Math.max(...chunk.map(vehicleCount), 0)
    });
  }
  return bins;
}

function trackKind(track: Track): OccupancyPoint["kind"] {
  if (track.class_id === 0) {
    return "person";
  }
  if ([2, 3, 5, 7].includes(track.class_id)) {
    return "vehicle";
  }
  return "other";
}

function buildOccupancyMap(reports: FrameReport[]) {
  const observedTracks = reports.flatMap(dynamicTracks);
  const worldTracks = observedTracks
    .filter((track) => finiteNumber(track.ground_x_m) && finiteNumber(track.ground_y_m))
    .map((track) => ({
      kind: trackKind(track),
      x: track.ground_x_m as number,
      y: track.ground_y_m as number
    }));
  const xValues = worldTracks.map(({ x }) => x);
  const yValues = worldTracks.map(({ y }) => y);
  const minX = Math.min(...xValues, 0);
  const maxX = Math.max(...xValues, 1);
  const minY = Math.min(...yValues, 0);
  const maxY = Math.max(...yValues, 1);

  const bandCounts = Array.from({ length: OCCUPANCY_BANDS }, () => 0);
  const pointBins = new Map<string, number>();
  for (const track of worldTracks) {
    const normalizedX = (track.x - minX) / Math.max(maxX - minX, 1e-6);
    const bandIndex = Math.min(
      OCCUPANCY_BANDS - 1,
      Math.max(0, Math.floor(normalizedX * OCCUPANCY_BANDS))
    );
    const binX = Math.min(11, Math.max(0, Math.floor(normalizedX * 12)));
    const binY = Math.min(7, Math.max(0, Math.floor(((track.y - minY) / Math.max(maxY - minY, 1e-6)) * 8)));
    bandCounts[bandIndex] += 1;
    pointBins.set(`${binX}:${binY}`, (pointBins.get(`${binX}:${binY}`) ?? 0) + 1);
  }

  const maxPointCount = Math.max(...Array.from(pointBins.values()), 1);
  const points = worldTracks.slice(-42).map((track, index): OccupancyPoint => {
    const normalizedX = (track.x - minX) / Math.max(maxX - minX, 1e-6);
    const normalizedY = (track.y - minY) / Math.max(maxY - minY, 1e-6);
    const binX = Math.min(11, Math.max(0, Math.floor(normalizedX * 12)));
    const binY = Math.min(7, Math.max(0, Math.floor(normalizedY * 8)));
    return {
      intensity: (pointBins.get(`${binX}:${binY}`) ?? 1) / maxPointCount,
      key: `${track.x}:${track.y}:${index}`,
      kind: track.kind,
      xPct: 12 + normalizedX * 76,
      yPct: 82 - normalizedY * 64
    };
  });

  const maxBandCount = Math.max(...bandCounts, 1);
  const bands = bandCounts.map((count, index): OccupancyBand => {
    const ratio = count / maxBandCount;
    return {
      count,
      label: index === 0 ? "左侧" : index === OCCUPANCY_BANDS - 1 ? "右侧" : `通道 ${index + 1}`,
      widthPct: 9 + ratio * 16,
      xPct: 16 + index * (68 / Math.max(OCCUPANCY_BANDS - 1, 1))
    };
  });

  return {
    bands,
    points,
    trackCount: observedTracks.length
  };
}

function bandLabel(band: OccupancyBand) {
  if (band.count === 0) {
    return `${band.label} 空闲`;
  }
  return `${band.label} ${band.count} 个样本`;
}

function pointClassName(point: OccupancyPoint) {
  return ["occupancy-point", `occupancy-point-${point.kind}`].join(" ");
}

function pointRadius(point: OccupancyPoint) {
  return 2.8 + point.intensity * 4.2;
}

function pointOpacity(point: OccupancyPoint) {
  return 0.42 + point.intensity * 0.48;
}

function OccupancyMap({ bands, points }: { bands: OccupancyBand[]; points: OccupancyPoint[] }) {
  return (
    <svg className="occupancy-map" role="img" viewBox="0 0 320 184">
      <title>空间占用鸟瞰图</title>
      <defs>
        <linearGradient id="occupancy-road-gradient" x1="0%" x2="100%" y1="0%" y2="100%">
          <stop offset="0%" stopColor="#0f2438" />
          <stop offset="100%" stopColor="#07111e" />
        </linearGradient>
        <filter id="occupancy-glow">
          <feGaussianBlur stdDeviation="4" />
        </filter>
      </defs>
      <path
        className="occupancy-road"
        d="M54 18 C92 31 230 26 268 14 L292 166 C234 154 87 155 30 171 Z"
      />
      <path className="occupancy-crosswalk" d="M61 123 L282 112 L286 131 L55 143 Z" />
      <path className="occupancy-lane" d="M78 44 C126 55 205 52 254 40" />
      <path className="occupancy-lane" d="M68 86 C126 96 218 93 270 79" />
      <path className="occupancy-lane" d="M52 146 C121 137 220 137 288 150" />
      <path className="occupancy-flow-arrow" d="M158 155 C169 124 172 78 164 34" />
      <path className="occupancy-flow-arrow-head" d="M164 30 L155 45 L174 42 Z" />
      {bands.map((band) => (
        <g key={band.label}>
          <title>{bandLabel(band)}</title>
          <ellipse
            className="occupancy-band-glow"
            cx={(band.xPct / 100) * 320}
            cy="98"
            filter="url(#occupancy-glow)"
            rx={(band.widthPct / 100) * 320}
            ry="54"
          />
          <ellipse
            className="occupancy-band"
            cx={(band.xPct / 100) * 320}
            cy="98"
            rx={(band.widthPct / 100) * 320}
            ry="48"
          />
        </g>
      ))}
      {points.map((point) => (
        <circle
          className={pointClassName(point)}
          cx={(point.xPct / 100) * 320}
          cy={(point.yPct / 100) * 184}
          key={point.key}
          r={pointRadius(point)}
          style={{ opacity: pointOpacity(point) }}
        />
      ))}
      <text className="occupancy-label occupancy-label-top" x="24" y="31">
        入口方向
      </text>
      <text className="occupancy-label occupancy-label-bottom" x="218" y="160">
        交互区域
      </text>
    </svg>
  );
}

function OccupancyLegend() {
  return (
    <div className="occupancy-legend">
      <span className="occupancy-legend-vehicle">车辆轨迹</span>
      <span className="occupancy-legend-person">行人轨迹</span>
      <span className="occupancy-legend-band">高占用带</span>
    </div>
  );
}

function EmptyOccupancyMap() {
  return (
    <div className="occupancy-empty">
      <span>等待地面坐标样本</span>
      <small>接入视频后显示鸟瞰占用路径</small>
    </div>
  );
}

function OccupancyCard({ bands, points }: { bands: OccupancyBand[]; points: OccupancyPoint[] }) {
  return (
    <div className="occupancy-card">
      <div>
        <h3>空间占用鸟瞰图</h3>
        <p>用地面坐标重建通行区域，圆点表示目标轨迹，亮带表示占用更集中的空间走廊。</p>
      </div>
      <div className="occupancy-map-shell">
        {points.length > 0 ? <OccupancyMap bands={bands} points={points} /> : <EmptyOccupancyMap />}
        <OccupancyLegend />
      </div>
    </div>
  );
}

function TrackSampleMetric({ trackCount }: { trackCount: number }) {
  return (
    <div>
      <span>空间轨迹样本</span>
      <strong>{trackCount}</strong>
    </div>
  );
}

function FlowMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function FlowMetrics({
  currentPeople,
  currentReport,
  currentVehicles,
  trackCount
}: {
  currentPeople: number;
  currentReport: FrameReport;
  currentVehicles: number;
  trackCount: number;
}) {
  return (
    <div className="flow-metric-row">
      <FlowMetric label="当前车辆" value={currentVehicles} />
      <FlowMetric label="当前行人" value={currentPeople} />
      <FlowMetric label="流量 q" value={formatMetric(currentReport.traffic_flow?.flow_q_veh_per_hour, " veh/h")} />
      <FlowMetric label="密度 k" value={formatMetric(currentReport.traffic_flow?.density_k_veh_per_km, " veh/km")} />
      <FlowMetric label="速度 v" value={formatMetric(latestValidSpeed(currentReport), " km/h")} />
      <TrackSampleMetric trackCount={trackCount} />
    </div>
  );
}

function FlowPlot({ bins, currentReport }: { bins: FlowBin[]; currentReport: FrameReport }) {
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

  return (
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
          const showAxisLabel = shouldShowAxisLabel(index, bins.length);
          return (
            <g key={`${bin.label}:${index}`}>
              <title>{bin.label}</title>
              <rect className="flow-bar" height={height} rx="5" width="28" x={x} y={180 - height} />
              {showAxisLabel && (
                <text className="flow-axis-label" x={x + 14} y="204">
                  {bin.axisLabel}
                </text>
              )}
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
  );
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

export function FlowChart({ className = "", history, report }: FlowChartProps) {
  const rootClassName = ["panel", "wide", className].filter(Boolean).join(" ");
  const reports = latestReports(report, history);
  if (reports.length === 0) {
    return (
      <section className={rootClassName}>
        <div className="panel-heading">
          <h2>流量趋势</h2>
        </div>
        <div className="empty-state">等待真实分析数据</div>
      </section>
    );
  }

  const bins = buildBins(reports);
  const currentReport = report ?? reports[reports.length - 1];
  const occupancy = buildOccupancyMap(reports);
  const currentPeople = peopleCount(currentReport);
  const currentVehicles = vehicleCount(currentReport);

  return (
    <section className={rootClassName}>
      <div className="panel-heading">
        <h2>流量趋势</h2>
        <span className="panel-subtitle">q/k/v + 鸟瞰占用路径</span>
      </div>
      <div className="flow-dashboard">
        <FlowPlot bins={bins} currentReport={currentReport} />
        <OccupancyCard bands={occupancy.bands} points={occupancy.points} />
      </div>
      <FlowMetrics
        currentPeople={currentPeople}
        currentReport={currentReport}
        currentVehicles={currentVehicles}
        trackCount={occupancy.trackCount}
      />
    </section>
  );
}
