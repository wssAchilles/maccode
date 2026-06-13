import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';

export type DashboardStatusTone = 'success' | 'warning' | 'danger' | 'running';

export type DashboardStatusItem = {
  label: string;
  value: string;
  detail: string;
  tone: DashboardStatusTone;
  href?: string;
};

type DashboardStatusBarProps = {
  items: DashboardStatusItem[];
  actions?: ReactNode;
};

export function DashboardStatusBar({ actions, items }: DashboardStatusBarProps) {
  return (
    <section className="dashboard-status-bar" aria-label="驾驶舱运行状态">
      <div className="dashboard-status-items">
        {items.map((item) => {
          const content = (
            <>
              <span className={`status-pill tone-${item.tone}`}>{item.value}</span>
              <strong>{item.label}</strong>
              <small>{item.detail}</small>
            </>
          );
          return item.href ? (
            <Link className="dashboard-status-item" to={item.href} key={item.label}>
              {content}
            </Link>
          ) : (
            <div className="dashboard-status-item" key={item.label}>
              {content}
            </div>
          );
        })}
      </div>
      {actions ? <div className="dashboard-status-actions">{actions}</div> : null}
    </section>
  );
}
