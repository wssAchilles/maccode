import { useCallback } from 'react';
import { useDailyEvents, useDailySales, useEventDistribution } from '../api/hooks';
import { ChartPanel } from '../components/ChartPanel';
import { useChartFilter } from '../context/ChartFilterContext';
import { displayValue } from '../i18n/displayText';
import { lineOption, pieOption } from '../lib/chartOptions';
import type { ECElementEvent } from 'echarts/core';

function rawChartName(params: ECElementEvent) {
  const data = params.data;
  if (data && typeof data === 'object' && 'rawName' in data) {
    const rawName = (data as { rawName?: unknown }).rawName;
    if (rawName !== undefined && rawName !== null) {
      return String(rawName);
    }
  }
  return params.name ? String(params.name) : '';
}

export function BehaviorPage() {
  const events = useEventDistribution();
  const dailyEvents = useDailyEvents();
  const dailySales = useDailySales();
  const { pieFilter, setPieFilter, clearFilter } = useChartFilter();

  const PIE_ID = 'behavior-pie';

  const handlePieClick = useCallback(
    (params: ECElementEvent) => {
      const selectedName = rawChartName(params);
      if (selectedName) setPieFilter(selectedName, PIE_ID);
    },
    [setPieFilter],
  );

  const isFiltered = pieFilter.selectedName && pieFilter.sourceChartId === PIE_ID;

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">行为分析</span>
        <h1>行为转化与趋势分析</h1>
        <p>独立观察访问量、购买趋势和行为结构，为后续异常检测和转化漏斗扩展留出空间。</p>
      </section>
      {isFiltered ? (
        <div className="filter-banner">
          已筛选：<strong>{displayValue(pieFilter.selectedName, 'eventType')}</strong>
          <button type="button" onClick={() => clearFilter()}>
            清除筛选
          </button>
        </div>
      ) : null}
      <section className="content-grid">
        <ChartPanel title="行为类型占比" subtitle="事件类型分布" option={pieOption(events.data ?? [])} onChartClick={handlePieClick} />
        <ChartPanel title="每日事件趋势" subtitle="全量行为量趋势" option={lineOption(dailyEvents.data ?? [], '事件量', '#39d0c8')} />
        <ChartPanel title="每日销售额" subtitle="购买行为销售额" option={lineOption(dailySales.data ?? [], '销售额', '#f59e0b')} />
      </section>
    </>
  );
}
