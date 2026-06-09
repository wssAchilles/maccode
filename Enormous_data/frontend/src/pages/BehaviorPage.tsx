import { useDailyEvents, useDailySales, useEventDistribution } from '../api/hooks';
import { ChartPanel } from '../components/ChartPanel';
import { lineOption, pieOption } from '../lib/chartOptions';

export function BehaviorPage() {
  const events = useEventDistribution();
  const dailyEvents = useDailyEvents();
  const dailySales = useDailySales();

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">Behavior analytics</span>
        <h1>行为转化与趋势分析</h1>
        <p>独立观察访问量、购买趋势和行为结构，为后续异常检测和转化漏斗扩展留出空间。</p>
      </section>
      <section className="content-grid">
        <ChartPanel title="行为类型占比" subtitle="事件类型分布" option={pieOption(events.data ?? [])} />
        <ChartPanel title="每日事件趋势" subtitle="全量行为量趋势" option={lineOption(dailyEvents.data ?? [], '事件量', '#39d0c8')} />
        <ChartPanel title="每日销售额" subtitle="购买行为销售额" option={lineOption(dailySales.data ?? [], '销售额', '#f59e0b')} />
      </section>
    </>
  );
}
