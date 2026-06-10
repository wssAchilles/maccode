import { useDailyEvents, useDailySales, useEventDistribution, useTopCategories } from '../api/hooks';
import { ChartPanel } from '../components/ChartPanel';
import { ErrorBanner } from '../components/feedback/ErrorBanner';
import { Hero } from '../components/layout/Hero';
import { SummaryStrip } from '../features/dashboard/SummaryStrip';
import { barOption, lineOption, pieOption } from '../lib/chartOptions';
import { formatCurrency, formatNumber } from '../lib/format';

function topNamedValue(rows: Array<{ name: string; value: number }> = []) {
  return rows.reduce<{ name: string; value: number } | null>((best, row) => (!best || row.value > best.value ? row : best), null);
}

function topDateValue(rows: Array<{ date: string; value: number }> = []) {
  return rows.reduce<{ date: string; value: number } | null>((best, row) => (!best || row.value > best.value ? row : best), null);
}

export function DashboardPage() {
  const events = useEventDistribution();
  const dailyEvents = useDailyEvents();
  const dailySales = useDailySales();
  const categories = useTopCategories();
  const error = events.error || dailyEvents.error || dailySales.error || categories.error;
  const topEvent = topNamedValue(events.data);
  const peakEvents = topDateValue(dailyEvents.data);
  const peakSales = topDateValue(dailySales.data);
  const topCategory = topNamedValue(categories.data);

  return (
    <>
      <Hero />
      <ErrorBanner error={error} />
      <SummaryStrip />
      <section className="content-grid">
        <ChartPanel
          title="行为类型分布"
          subtitle="浏览、加购、移除购物车和购买的结构占比"
          option={pieOption(events.data ?? [])}
          summary={topEvent ? `${topEvent.name} 占比最高，共 ${formatNumber(topEvent.value)} 次。` : '等待行为类型数据。'}
        />
        <ChartPanel
          title="每日事件趋势"
          subtitle="按日期聚合后的用户行为量"
          option={lineOption(dailyEvents.data ?? [], '事件量', '#39d0c8')}
          summary={peakEvents ? `${peakEvents.date} 达到事件峰值 ${formatNumber(peakEvents.value)}。` : '等待每日事件趋势数据。'}
        />
        <ChartPanel
          title="每日销售额"
          subtitle="purchase 事件价格合计"
          option={lineOption(dailySales.data ?? [], '销售额', '#f59e0b')}
          summary={peakSales ? `${peakSales.date} 销售额最高，为 ${formatCurrency(peakSales.value)}。` : '等待每日销售额数据。'}
        />
        <ChartPanel
          title="类目排行"
          subtitle="一级类目事件量 TopN"
          option={barOption(categories.data ?? [], '事件量', '#7cdaff')}
          summary={topCategory ? `${topCategory.name} 是当前最高事件类目，共 ${formatNumber(topCategory.value)} 次。` : '等待类目排行数据。'}
        />
      </section>
    </>
  );
}
