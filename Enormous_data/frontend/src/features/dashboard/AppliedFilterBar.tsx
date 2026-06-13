import { X } from 'lucide-react';
import type { ReactNode } from 'react';
import type { DashboardFilter } from '../../context/ChartFilterContext';

type AppliedFilterBarProps = {
  action?: ReactNode;
  filters: DashboardFilter[];
  onClear: (field?: string) => void;
};

export function AppliedFilterBar({ action, filters, onClear }: AppliedFilterBarProps) {
  if (!filters.length) return null;

  return (
    <section className="applied-filter-bar" aria-label="当前图表筛选">
      <span>当前筛选</span>
      <div>
        {filters.map((filter) => (
          <button type="button" key={`${filter.field}-${filter.value}`} onClick={() => onClear(filter.field)}>
            <span>{filter.label}</span>
            {filter.sourceLabel ? <small>来自：{filter.sourceLabel}</small> : null}
            <X size={14} aria-hidden="true" />
          </button>
        ))}
      </div>
      <p>
        影响范围：
        {Array.from(new Set(filters.flatMap((filter) => filter.affects ?? ['图表高亮', '明细跳转']))).join('、')}
        ；当前聚合图保留全量口径作为对照。
      </p>
      <nav className="drill-path" aria-label="下钻路径">
        <span>下钻路径</span>
        <ol>
          <li>总览</li>
          {filters.map((filter) => (
            <li key={`path-${filter.field}-${filter.value}`}>{filter.label}</li>
          ))}
          <li>明细</li>
        </ol>
      </nav>
      <button type="button" className="clear-all-filter" onClick={() => onClear()}>
        清除全部
      </button>
      {action}
    </section>
  );
}
