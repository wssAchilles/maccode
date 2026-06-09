import type { ReactNode } from 'react';

type MetricCardProps = {
  label: string;
  value: ReactNode;
  detail: string;
  tone?: 'primary' | 'success' | 'warning' | 'danger';
};

export function MetricCard({ label, value, detail, tone = 'primary' }: MetricCardProps) {
  return (
    <article className={`metric-card tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}
