import type { ReactNode } from "react";

interface MetricTileProps {
  alert?: boolean;
  detail?: ReactNode;
  label: string;
  value: ReactNode;
  tone?: "neutral" | "green" | "blue" | "cyan" | "amber" | "red";
}

export function MetricTile({ alert = false, detail, label, value, tone = "neutral" }: MetricTileProps) {
  return (
    <section className={`metric-tile ${tone}${alert ? " alert" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail && <small>{detail}</small>}
    </section>
  );
}
