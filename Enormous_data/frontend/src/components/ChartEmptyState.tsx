type ChartEmptyStateProps = {
  title?: string;
  description?: string;
  actionHint?: string;
  tone?: 'empty' | 'loading' | 'error';
};

export function ChartEmptyState({
  title = '暂无图表数据',
  description = '当前筛选条件下没有可展示的数据点。',
  actionHint,
  tone = 'empty',
}: ChartEmptyStateProps) {
  return (
    <div className={`chart-panel-state tone-${tone}`} role={tone === 'error' ? 'alert' : 'status'} aria-live="polite">
      <strong>{title}</strong>
      <span>{description}</span>
      {actionHint ? <small>{actionHint}</small> : null}
    </div>
  );
}
