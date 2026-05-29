import { useEffect, useState } from "react";

import type { ZoneConfig as ZoneConfigType } from "../types/zoneConfig";

interface ZoneConfigProps {
  onSave: (zones: ZoneConfigType[]) => void;
  zones: ZoneConfigType[];
}

export function ZoneConfig({ onSave, zones }: ZoneConfigProps) {
  const [name, setName] = useState(zones[0]?.name ?? "");
  const [lineStartX, setLineStartX] = useState(zones[0] ? String(zones[0].line_start[0]) : "");
  const [lineEndX, setLineEndX] = useState(zones[0] ? String(zones[0].line_end[0]) : "");
  const [lineY, setLineY] = useState(zones[0] ? String(zones[0].line_start[1]) : "");

  useEffect(() => {
    setName(zones[0]?.name ?? "");
    setLineStartX(zones[0] ? String(zones[0].line_start[0]) : "");
    setLineEndX(zones[0] ? String(zones[0].line_end[0]) : "");
    setLineY(zones[0] ? String(zones[0].line_start[1]) : "");
  }, [zones]);

  function saveZone() {
    const x1 = Number(lineStartX);
    const x2 = Number(lineEndX);
    const y = Number(lineY);
    if (!name.trim() || !Number.isFinite(x1) || !Number.isFinite(x2) || !Number.isFinite(y)) {
      return;
    }
    onSave([{ name: name.trim(), line_start: [x1, y], line_end: [x2, y] }]);
  }

  const canSave =
    name.trim().length > 0 &&
    lineStartX.trim().length > 0 &&
    lineEndX.trim().length > 0 &&
    lineY.trim().length > 0 &&
    Number.isFinite(Number(lineStartX)) &&
    Number.isFinite(Number(lineEndX)) &&
    Number.isFinite(Number(lineY));

  return (
    <section className="panel page-panel">
      <div className="panel-heading">
        <h2>区域配置</h2>
        <button className="primary-button" disabled={!canSave} onClick={saveZone} type="button">
          保存配置
        </button>
      </div>
      <div className="zone-form">
        <label>
          区域名称
          <input onChange={(event) => setName(event.target.value)} value={name} />
        </label>
        <label>
          计数线起点 X
          <input onChange={(event) => setLineStartX(event.target.value)} type="number" value={lineStartX} />
        </label>
        <label>
          计数线终点 X
          <input onChange={(event) => setLineEndX(event.target.value)} type="number" value={lineEndX} />
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
