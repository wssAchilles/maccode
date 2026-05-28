import type { ZoneStats } from "../../types/frameReport";

interface ZoneStatsListProps {
  zones: ZoneStats[];
}

export function ZoneStatsList({ zones }: ZoneStatsListProps) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>区域统计</h2>
      </div>
      <div className="zone-list">
        {zones.map((zone) => (
          <div className="zone-row" key={zone.name}>
            <span>{zone.name}</span>
            <strong>{zone.in_count}</strong>
            <strong>{zone.out_count}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}
