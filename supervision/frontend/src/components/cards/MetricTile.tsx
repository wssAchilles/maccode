import type { ReactNode } from "react";

interface MetricTileProps {
  label: string;
  value: ReactNode;
  tone?: "neutral" | "green" | "blue";
}

export function MetricTile({ label, value, tone = "neutral" }: MetricTileProps) {
  return (
    <section className={`metric-tile ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </section>
  );
}
