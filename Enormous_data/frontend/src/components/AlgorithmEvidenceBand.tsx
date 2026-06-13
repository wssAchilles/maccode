import type { ReactNode } from 'react';

export type AlgorithmEvidenceTone = 'success' | 'warning' | 'danger' | 'running' | 'ready';

export type AlgorithmEvidenceMetric = {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
};

type AlgorithmEvidenceBandProps = {
  title: string;
  status: string;
  tone: AlgorithmEvidenceTone;
  description: ReactNode;
  metrics: AlgorithmEvidenceMetric[];
  icon?: ReactNode;
  caveat?: ReactNode;
};

export function AlgorithmEvidenceBand({ caveat, description, icon, metrics, status, title, tone }: AlgorithmEvidenceBandProps) {
  return (
    <section className="ops-command-band algorithm-evidence-band" aria-label={`${title}区域`}>
      <div className="algorithm-evidence-copy">
        <span className={`status-pill tone-${tone}`}>{status}</span>
        <h2>{title}</h2>
        <p>{description}</p>
        {caveat ? <small>{caveat}</small> : null}
      </div>
      <div className="algorithm-evidence-metrics" aria-label={`${title}关键证据`}>
        {metrics.map((metric) => (
          <span className="algorithm-evidence-metric" key={metric.label}>
            <small>{metric.label}</small>
            <strong>{metric.value}</strong>
            {metric.detail ? <em>{metric.detail}</em> : null}
          </span>
        ))}
      </div>
      {icon ? <div className="algorithm-evidence-icon" aria-hidden="true">{icon}</div> : null}
    </section>
  );
}
