import { animate, stagger } from 'animejs';
import { useEffect, useMemo } from 'react';
import { useEventDistribution, useSummary } from '../../api/hooks';
import { formatCurrency, formatNumber } from '../../lib/format';
import { MetricCard } from '../../components/MetricCard';
import { LoadingState } from '../../components/feedback/LoadingState';

export function SummaryStrip() {
  const summary = useSummary();
  const events = useEventDistribution();

  useEffect(() => {
    if (!summary.data) return;
    animate('.metric-card', {
      translateY: [18, 0],
      opacity: [0, 1],
      delay: stagger(70),
      duration: 620,
      ease: 'out(3)',
    });
  }, [summary.data]);

  const conversionRate = useMemo(() => {
    const rows = events.data ?? [];
    const views = rows.find((row) => row.name === 'view')?.value ?? 0;
    const purchases = rows.find((row) => row.name === 'purchase')?.value ?? 0;
    return views ? (purchases / views) * 100 : 0;
  }, [events.data]);

  if (summary.isLoading) return <LoadingState />;

  return (
    <section className="metrics-strip">
      <MetricCard label="有效事件" value={formatNumber(summary.data?.cleaned_rows)} detail="清洗去重后记录数" />
      <MetricCard label="销售额" value={formatCurrency(summary.data?.total_sales)} detail="purchase 行为金额合计" tone="success" />
      <MetricCard label="用户数" value={formatNumber(summary.data?.unique_users)} detail="distinct user_id" />
      <MetricCard label="转化率" value={formatNumber(conversionRate, '%')} detail="purchase / view" tone="warning" />
    </section>
  );
}
