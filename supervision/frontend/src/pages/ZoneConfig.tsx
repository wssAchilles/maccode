import { useEffect, useState } from "react";

import type { ZoneConfig as ZoneConfigType } from "../types/zoneConfig";

interface ZoneConfigProps {
  onSave: (zones: ZoneConfigType[]) => void;
  zones: ZoneConfigType[];
}

export function ZoneConfig({ onSave, zones }: ZoneConfigProps) {
  const [name, setName] = useState(zones[0]?.name ?? "main_gate");
  const [lineY, setLineY] = useState(String(zones[0]?.line_start[1] ?? 10));

  useEffect(() => {
    setName(zones[0]?.name ?? "main_gate");
    setLineY(String(zones[0]?.line_start[1] ?? 10));
  }, [zones]);

  function saveZone() {
    const y = Number(lineY);
    onSave([{ name, line_start: [0, y], line_end: [100, y] }]);
  }

  return (
    <section className="panel page-panel">
      <div className="panel-heading">
        <h2>区域配置</h2>
        <button className="primary-button" onClick={saveZone} type="button">
          保存配置
        </button>
      </div>
      <div className="zone-form">
        <label>
          区域名称
          <input onChange={(event) => setName(event.target.value)} value={name} />
        </label>
        <label>
          计数线 Y 坐标
          <input onChange={(event) => setLineY(event.target.value)} type="number" value={lineY} />
        </label>
      </div>
      <div className="zone-config-list">
        {zones.map((zone) => (
          <div className="zone-config-row" key={zone.name}>
            <strong>{zone.name}</strong>
            <span>
              [{zone.line_start.join(", ")}] → [{zone.line_end.join(", ")}]
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
