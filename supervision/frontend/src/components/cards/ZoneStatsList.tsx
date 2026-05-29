import type { FrameReport } from "../../types/frameReport";
import { formatCount } from "../../utils/formatters";

interface ZoneStatsListProps {
  report: FrameReport | null;
}

function formatDensity(value: number | null | undefined) {
  return value === null || value === undefined ? "待建模" : `${value.toFixed(2)} 人/m²`;
}

function formatTrafficDensity(value: number | null | undefined) {
  return value === null || value === undefined ? "待建模" : `${value.toFixed(1)} veh/km`;
}

function formatCountWithUnit(value: number | null | undefined, unit: string) {
  return value === null || value === undefined ? "待建模" : `${formatCount(value)} ${unit}`;
}

export function ZoneStatsList({ report }: ZoneStatsListProps) {
  const zones = report?.zone_stats ?? [];
  const regionalPeople = report?.regional_people_count ?? null;
  const trafficFlow = report?.traffic_flow ?? null;
  const vehicles = report?.infrastructure_semantics?.dynamic_vehicle_count;
  const hasCrossingEvent = zones.some((zone) => zone.in_count > 0 || zone.out_count > 0);

  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>区域统计</h2>
      </div>
      <div className="zone-metric-grid">
        <div>
          <span>当前区域占用</span>
          <strong>{formatCountWithUnit(regionalPeople?.people_count, "人")}</strong>
        </div>
        <div>
          <span>区域车辆观测</span>
          <strong>{formatCountWithUnit(vehicles, "辆")}</strong>
        </div>
        <div>
          <span>人群密度</span>
          <strong>{formatDensity(regionalPeople?.density_people_per_sqm)}</strong>
        </div>
        <div>
          <span>交通流密度 k</span>
          <strong>{formatTrafficDensity(trafficFlow?.density_k_veh_per_km)}</strong>
        </div>
      </div>
      <div className="zone-list">
        {zones.length === 0 ? (
          <div className="empty-state">等待真实分析数据</div>
        ) : (
          <>
            <div className="zone-row zone-row-header">
              <span>统计线/区域</span>
              <strong>进入</strong>
              <strong>离开</strong>
            </div>
            {zones.map((zone) => (
              <div className="zone-row" key={zone.name}>
                <span>{zone.name}</span>
                <strong>{formatCount(zone.in_count)}</strong>
                <strong>{formatCount(zone.out_count)}</strong>
              </div>
            ))}
            {!hasCrossingEvent && (
              <p className="zone-note">
                当前 0/0 表示没有目标穿越配置的统计线；区域人数和密度来自当前帧占用建模，不等同于过线流量。
              </p>
            )}
          </>
        )}
      </div>
    </section>
  );
}
