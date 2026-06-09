import { useDailyEvents, useDailySales, useEventDistribution, useTopCategories } from '../api/hooks';
import { ChartPanel } from '../components/ChartPanel';
import { ErrorBanner } from '../components/feedback/ErrorBanner';
import { Hero } from '../components/layout/Hero';
import { SummaryStrip } from '../features/dashboard/SummaryStrip';
import { barOption, lineOption, pieOption } from '../lib/chartOptions';

export function DashboardPage() {
  const events = useEventDistribution();
  const dailyEvents = useDailyEvents();
  const dailySales = useDailySales();
  const categories = useTopCategories();
  const error = events.error || dailyEvents.error || dailySales.error || categories.error;

  return (
    <>
      <Hero />
      <ErrorBanner error={error} />
      <SummaryStrip />
      <section className="content-grid">
        <ChartPanel title="行为类型分布" subtitle="浏览、加购、移除购物车和购买的结构占比" option={pieOption(events.data ?? [])} />
        <ChartPanel title="每日事件趋势" subtitle="按日期聚合后的用户行为量" option={lineOption(dailyEvents.data ?? [], '事件量', '#39d0c8')} />
        <ChartPanel title="每日销售额" subtitle="purchase 事件价格合计" option={lineOption(dailySales.data ?? [], '销售额', '#f59e0b')} />
        <ChartPanel title="类目排行" subtitle="一级类目事件量 TopN" option={barOption(categories.data ?? [], '事件量', '#7cdaff')} />
      </section>
    </>
  );
}
