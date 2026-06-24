import { useCallback, useMemo } from 'react';
import { Activity, BarChart3, CalendarDays, FilterX, MousePointerClick, ShoppingCart, Target, TrendingUp } from 'lucide-react';
import type { ECElementEvent } from 'echarts/core';
import { useDailyEvents, useDailySales, useEventDistribution } from '../api/hooks';
import { ChartPanel, type DashboardChartOption } from '../components/ChartPanel';
import { useChartFilter } from '../context/ChartFilterContext';
import { displayValue } from '../i18n/displayText';
import type { DateValue, NamedValue } from '../types/api';

type BehaviorKey = 'view' | 'cart' | 'purchase' | string;

const behaviorColors: Record<string, string> = {
  view: '#4f7cff',
  cart: '#b6e848',
  purchase: '#f59e0b',
};

const behaviorRoles: Record<string, string> = {
  view: '流量入口，判断商品曝光是否足够。',
  cart: '购买意图，判断用户是否进入决策池。',
  purchase: '成交结果，判断最终转化与收入贡献。',
};

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

function numberValue(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatNumber(value: number, digits = 0) {
  return value.toLocaleString('zh-CN', { maximumFractionDigits: digits });
}

function formatMoney(value: number) {
  return `¥${value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`;
}

function formatPercent(value: number) {
  if (!Number.isFinite(value)) return '0.0%';
  return `${(value * 100).toFixed(1)}%`;
}

function eventValue(rows: NamedValue[], key: BehaviorKey) {
  return rows.find((row) => row.name === key)?.value ?? 0;
}

function maxDateValue(rows: DateValue[]) {
  return rows.reduce<DateValue | null>((best, row) => (!best || numberValue(row.value) > numberValue(best.value) ? row : best), null);
}

function average(rows: DateValue[]) {
  if (!rows.length) return 0;
  return rows.reduce((sum, row) => sum + numberValue(row.value), 0) / rows.length;
}

function dateSpan(rows: DateValue[]) {
  if (!rows.length) return '暂无时间窗';
  const dates = rows.map((row) => row.date).sort();
  return `${dates[0]} 至 ${dates[dates.length - 1]}`;
}

function shareOption(rows: NamedValue[], selectedName?: string | null): DashboardChartOption {
  const total = rows.reduce((sum, row) => sum + numberValue(row.value), 0);
  const chartRows = rows.map((row) => ({
    name: displayValue(row.name, 'eventType'),
    rawName: row.name,
    value: numberValue(row.value),
    itemStyle: {
      color: behaviorColors[row.name] ?? '#60a5fa',
      opacity: !selectedName || selectedName === row.name ? 1 : 0.28,
    },
  }));

  return {
    textStyle: { fontFamily: 'Inter, "Microsoft YaHei", system-ui, sans-serif', color: '#d8e2ee' },
    color: rows.map((row) => behaviorColors[row.name] ?? '#60a5fa'),
    tooltip: {
      trigger: 'item',
      formatter: (params: unknown) => {
        const row = params as { marker?: string; name?: string; value?: number; percent?: number };
        return `${row.marker ?? ''}${row.name ?? ''}<br/>事件量：${formatNumber(numberValue(row.value))}<br/>占比：${(row.percent ?? 0).toFixed(2)}%`;
      },
    },
    legend: {
      bottom: 8,
      textStyle: { color: '#9fb2c8' },
    },
    series: [
      {
        name: '行为类型',
        type: 'pie',
        radius: ['58%', '76%'],
        center: ['50%', '46%'],
        avoidLabelOverlap: true,
        minAngle: 4,
        label: {
          color: '#cbd5e1',
          formatter: '{b}\n{d}%',
        },
        labelLine: {
          length: 16,
          length2: 12,
          lineStyle: { color: '#64748b' },
        },
        itemStyle: {
          borderColor: '#0a0f17',
          borderWidth: 3,
        },
        data: chartRows,
      },
    ],
  };
}

function trendOption(eventRows: DateValue[], salesRows: DateValue[]): DashboardChartOption {
  const dates = Array.from(new Set([...eventRows.map((row) => row.date), ...salesRows.map((row) => row.date)])).sort();
  const eventMap = new Map(eventRows.map((row) => [row.date, numberValue(row.value)]));
  const salesMap = new Map(salesRows.map((row) => [row.date, numberValue(row.value)]));
  const showZoom = dates.length > 14;

  return {
    textStyle: { fontFamily: 'Inter, "Microsoft YaHei", system-ui, sans-serif', color: '#d8e2ee' },
    color: ['#39d0c8', '#f59e0b'],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: unknown) => {
        const rows = Array.isArray(params) ? (params as Array<{ marker?: string; seriesName?: string; value?: number }>) : [];
        const title = rows[0] ? `<strong>${(rows[0] as { axisValue?: string }).axisValue ?? ''}</strong>` : '';
        const lines = rows.map((row) => {
          const value = row.seriesName === '成交额' ? formatMoney(numberValue(row.value)) : formatNumber(numberValue(row.value));
          return `${row.marker ?? ''}${row.seriesName ?? ''}：${value}`;
        });
        return [title, ...lines].join('<br/>');
      },
    },
    legend: {
      top: 8,
      textStyle: { color: '#9fb2c8' },
    },
    grid: {
      left: 62,
      right: 76,
      top: 56,
      bottom: showZoom ? 78 : 42,
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { color: '#9fb2c8' },
      axisLine: { lineStyle: { color: '#263244' } },
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        name: '事件量',
        nameTextStyle: { color: '#9fb2c8' },
        axisLabel: { color: '#9fb2c8' },
        splitLine: { lineStyle: { color: '#223047' } },
      },
      {
        type: 'value',
        name: '成交额',
        nameTextStyle: { color: '#9fb2c8' },
        axisLabel: {
          color: '#9fb2c8',
          formatter: (value: number) => `${Math.round(value / 1000)}k`,
        },
        splitLine: { show: false },
      },
    ],
    dataZoom: showZoom
      ? [
          {
            type: 'slider',
            height: 18,
            bottom: 24,
            borderColor: 'rgba(96, 165, 250, 0.24)',
            fillerColor: 'rgba(57, 208, 200, 0.28)',
            dataBackground: { lineStyle: { color: '#39d0c8' }, areaStyle: { color: 'rgba(57, 208, 200, 0.12)' } },
            textStyle: { color: '#9fb2c8' },
          },
          { type: 'inside' },
        ]
      : [],
    series: [
      {
        name: '事件量',
        type: 'line',
        smooth: true,
        symbolSize: 6,
        lineStyle: { width: 3 },
        areaStyle: { color: 'rgba(57, 208, 200, 0.12)' },
        data: dates.map((date) => eventMap.get(date) ?? 0),
      },
      {
        name: '成交额',
        type: 'bar',
        yAxisIndex: 1,
        barMaxWidth: 12,
        itemStyle: { borderRadius: [5, 5, 0, 0] },
        data: dates.map((date) => salesMap.get(date) ?? 0),
      },
    ],
  };
}

export function BehaviorPage() {
  const events = useEventDistribution();
  const dailyEvents = useDailyEvents();
  const dailySales = useDailySales();
  const { pieFilter, setPieFilter, clearFilter } = useChartFilter();

  const PIE_ID = 'behavior-pie';
  const eventRows = events.data ?? [];
  const dailyEventRows = dailyEvents.data ?? [];
  const dailySalesRows = dailySales.data ?? [];

  const handlePieClick = useCallback(
    (params: ECElementEvent) => {
      const selectedName = rawChartName(params);
      if (selectedName) setPieFilter(selectedName, PIE_ID);
    },
    [setPieFilter],
  );

  const selectedEvent = pieFilter.sourceChartId === PIE_ID ? pieFilter.selectedName : undefined;
  const isFiltered = Boolean(selectedEvent);

  const metrics = useMemo(() => {
    const totalEvents = eventRows.reduce((sum, row) => sum + numberValue(row.value), 0);
    const viewCount = eventValue(eventRows, 'view');
    const cartCount = eventValue(eventRows, 'cart');
    const purchaseCount = eventValue(eventRows, 'purchase');
    const totalSales = dailySalesRows.reduce((sum, row) => sum + numberValue(row.value), 0);
    const peakEvents = maxDateValue(dailyEventRows);
    const peakSales = maxDateValue(dailySalesRows);
    return {
      totalEvents,
      viewCount,
      cartCount,
      purchaseCount,
      totalSales,
      cartRate: viewCount ? cartCount / viewCount : 0,
      purchaseRate: viewCount ? purchaseCount / viewCount : 0,
      cartToPurchaseRate: cartCount ? purchaseCount / cartCount : 0,
      avgDailyEvents: average(dailyEventRows),
      avgDailySales: average(dailySalesRows),
      peakEvents,
      peakSales,
      span: dateSpan(dailyEventRows),
    };
  }, [dailyEventRows, dailySalesRows, eventRows]);

  const selectedEventRow = eventRows.find((row) => row.name === selectedEvent);
  const selectedShare = selectedEventRow && metrics.totalEvents ? selectedEventRow.value / metrics.totalEvents : 0;

  const behaviorSteps = [
    {
      key: 'view',
      label: displayValue('view', 'eventType'),
      value: metrics.viewCount,
      rate: metrics.totalEvents ? metrics.viewCount / metrics.totalEvents : 0,
      icon: MousePointerClick,
      action: '先确认曝光基盘',
    },
    {
      key: 'cart',
      label: displayValue('cart', 'eventType'),
      value: metrics.cartCount,
      rate: metrics.viewCount ? metrics.cartCount / metrics.viewCount : 0,
      icon: ShoppingCart,
      action: '观察加购意图',
    },
    {
      key: 'purchase',
      label: displayValue('purchase', 'eventType'),
      value: metrics.purchaseCount,
      rate: metrics.viewCount ? metrics.purchaseCount / metrics.viewCount : 0,
      icon: Target,
      action: '定位成交结果',
    },
  ];

  return (
    <>
      <section className="page-heading behavior-heading">
        <span className="eyebrow">行为分析</span>
        <h1>行为转化与趋势分析</h1>
        <p>把浏览、加购和购买拆成可点击的行为链路：先看结构，再看趋势峰值，最后定位转化缺口。</p>
      </section>

      <section className="behavior-command-center">
        <div className="behavior-command-main">
          <span className="status-pill tone-success">分析就绪</span>
          <h2>从事件日志到转化判断</h2>
          <p>当前页只展示 2019 历史电商行为的聚合结果；点击行为类型会高亮该事件，并同步右侧解释与下方作战卡。</p>
          <div className="behavior-flow-steps">
            {behaviorSteps.map((step, index) => {
              const Icon = step.icon;
              return (
                <button
                  className={`behavior-flow-step ${selectedEvent === step.key ? 'is-active' : ''}`}
                  key={step.key}
                  type="button"
                  onClick={() => setPieFilter(step.key, PIE_ID)}
                >
                  <span>0{index + 1}</span>
                  <Icon aria-hidden="true" size={18} />
                  <strong>{step.label}</strong>
                  <small>{step.action}</small>
                </button>
              );
            })}
          </div>
        </div>
        <aside className="behavior-selection-card" aria-label="当前行为筛选解释">
          <div>
            <span className="eyebrow">当前观察对象</span>
            <strong>{selectedEvent ? displayValue(selectedEvent, 'eventType') : '全部行为'}</strong>
            <p>
              {selectedEvent
                ? `${displayValue(selectedEvent, 'eventType')}占全部行为 ${formatPercent(selectedShare)}。${behaviorRoles[selectedEvent] ?? '用于观察该事件在全链路中的占比。'}`
                : '未选择单一事件，所有图表显示全站行为结构与日级趋势。'}
            </p>
          </div>
          <button type="button" onClick={() => clearFilter()} disabled={!isFiltered}>
            <FilterX size={16} aria-hidden="true" />
            清除筛选
          </button>
        </aside>
      </section>

      <section className="behavior-metric-grid" aria-label="行为分析核心指标">
        <div className="behavior-metric-card">
          <Activity size={18} aria-hidden="true" />
          <span>总行为量</span>
          <strong>{formatNumber(metrics.totalEvents)}</strong>
          <small>{metrics.span}</small>
        </div>
        <div className="behavior-metric-card">
          <ShoppingCart size={18} aria-hidden="true" />
          <span>浏览到加购</span>
          <strong>{formatPercent(metrics.cartRate)}</strong>
          <small>{formatNumber(metrics.cartCount)} 次加购 / {formatNumber(metrics.viewCount)} 次浏览</small>
        </div>
        <div className="behavior-metric-card">
          <Target size={18} aria-hidden="true" />
          <span>浏览到购买</span>
          <strong>{formatPercent(metrics.purchaseRate)}</strong>
          <small>{formatNumber(metrics.purchaseCount)} 次购买 / {formatNumber(metrics.viewCount)} 次浏览</small>
        </div>
        <div className="behavior-metric-card">
          <TrendingUp size={18} aria-hidden="true" />
          <span>购买成交额</span>
          <strong>{formatMoney(metrics.totalSales)}</strong>
          <small>日均 {formatMoney(metrics.avgDailySales)}</small>
        </div>
      </section>

      {isFiltered ? (
        <div className="filter-banner">
          已筛选：<strong>{displayValue(selectedEvent, 'eventType')}</strong>
          <span>筛选用于解释当前行为，不会改写后端聚合缓存。</span>
          <button type="button" onClick={() => clearFilter()}>
            清除筛选
          </button>
        </div>
      ) : null}

      <section className="behavior-analysis-grid">
        <ChartPanel
          title="行为类型占比"
          subtitle="点击扇区或上方步骤，查看该行为在转化链路中的角色"
          option={shareOption(eventRows, selectedEvent)}
          chartId={PIE_ID}
          onChartClick={handlePieClick}
          isLoading={events.isLoading}
          error={events.error}
          isEmpty={!eventRows.length}
          annotations={[
            { label: '全量事件', value: formatNumber(metrics.totalEvents), tone: 'info' },
            { label: '当前选择', value: selectedEvent ? displayValue(selectedEvent, 'eventType') : '全部', tone: selectedEvent ? 'success' : 'info' },
          ]}
          filterNotice={selectedEvent ? `当前高亮 ${displayValue(selectedEvent, 'eventType')}，占比 ${formatPercent(selectedShare)}。` : undefined}
          summary={`浏览是流量入口，加购是意图信号，购买是成交结果。当前浏览占比 ${formatPercent(metrics.totalEvents ? metrics.viewCount / metrics.totalEvents : 0)}。`}
        />

        <ChartPanel
          title="事件量与成交额趋势"
          subtitle="用同一时间轴观察流量峰值是否带来成交峰值"
          option={trendOption(dailyEventRows, dailySalesRows)}
          isLoading={dailyEvents.isLoading || dailySales.isLoading}
          error={dailyEvents.error ?? dailySales.error}
          isEmpty={!dailyEventRows.length && !dailySalesRows.length}
          annotations={[
            { label: '事件峰值', value: metrics.peakEvents ? `${metrics.peakEvents.date} · ${formatNumber(metrics.peakEvents.value)}` : '暂无', tone: 'warning' },
            { label: '成交峰值', value: metrics.peakSales ? `${metrics.peakSales.date} · ${formatMoney(metrics.peakSales.value)}` : '暂无', tone: 'success' },
          ]}
          summary={`日均事件量 ${formatNumber(metrics.avgDailyEvents, 1)}，成交额日均 ${formatMoney(metrics.avgDailySales)}。峰值用于后续异常雷达和营收归因定位。`}
        />
      </section>

      <section className="behavior-lower-grid">
        <div className="data-panel behavior-funnel-panel">
          <div className="panel-title">
            <div>
              <h2>转化漏斗缺口</h2>
              <p>把浏览、加购、购买放到同一条链路里，回答“流量掉在哪里”。</p>
            </div>
            <BarChart3 size={22} aria-hidden="true" />
          </div>
          <div className="behavior-funnel">
            {behaviorSteps.map((step, index) => {
              const width = metrics.viewCount ? Math.max(4, (step.value / metrics.viewCount) * 100) : 0;
              return (
                <button
                  className={`behavior-funnel-row ${selectedEvent === step.key ? 'is-active' : ''}`}
                  key={step.key}
                  type="button"
                  onClick={() => setPieFilter(step.key, PIE_ID)}
                >
                  <span>{step.label}</span>
                  <strong>{formatNumber(step.value)}</strong>
                  <div className="behavior-funnel-track" aria-hidden="true">
                    <i style={{ width: `${width}%` }} />
                  </div>
                  <small>{index === 0 ? '流量基准' : `相对浏览 ${formatPercent(step.rate)}`}</small>
                </button>
              );
            })}
          </div>
          <p className="behavior-explain-box">
            当前加购到购买转化为 {formatPercent(metrics.cartToPurchaseRate)}。如果加购率高但购买率低，应优先检查价格、库存、优惠和结算体验。
          </p>
        </div>

        <div className="data-panel behavior-peak-panel">
          <div className="panel-title">
            <div>
              <h2>峰值解释器</h2>
              <p>把异常高峰从折线图中抽出来，方便答辩时说明观察结论。</p>
            </div>
            <CalendarDays size={22} aria-hidden="true" />
          </div>
          <div className="behavior-peak-grid">
            <div>
              <span>事件峰值日</span>
              <strong>{metrics.peakEvents?.date ?? '暂无'}</strong>
              <small>{metrics.peakEvents ? `${formatNumber(metrics.peakEvents.value)} 次事件` : '无日级事件'}</small>
            </div>
            <div>
              <span>成交峰值日</span>
              <strong>{metrics.peakSales?.date ?? '暂无'}</strong>
              <small>{metrics.peakSales ? formatMoney(metrics.peakSales.value) : '无日级成交'}</small>
            </div>
            <div>
              <span>观测窗口</span>
              <strong>{dailyEventRows.length || dailySalesRows.length} 天</strong>
              <small>来自 Spark 清洗后的日级缓存</small>
            </div>
          </div>
          <p className="behavior-explain-box">
            如果事件峰值和成交峰值同日出现，说明流量放大可能带来成交；如果不同日，则需要结合购物车召回、营收归因或异常雷达进一步解释。
          </p>
        </div>
      </section>

      <section className="data-panel behavior-event-workbench">
        <div className="panel-title">
          <div>
            <h2>行为类型作战卡</h2>
            <p>每个行为都有入口、占比、业务含义和下一步动作；点击卡片会联动上方占比图。</p>
          </div>
        </div>
        <div className="behavior-event-card-grid">
          {eventRows.map((row) => {
            const share = metrics.totalEvents ? numberValue(row.value) / metrics.totalEvents : 0;
            return (
              <button
                className={`behavior-event-card ${selectedEvent === row.name ? 'is-active' : ''}`}
                key={row.name}
                type="button"
                onClick={() => setPieFilter(row.name, PIE_ID)}
              >
                <span>{displayValue(row.name, 'eventType')}</span>
                <strong>{formatNumber(row.value)}</strong>
                <small>占全部行为 {formatPercent(share)}</small>
                <i aria-hidden="true">
                  <b style={{ width: `${Math.max(3, share * 100)}%` }} />
                </i>
                <em>{behaviorRoles[row.name] ?? '用于补充观察该事件类型。'}</em>
              </button>
            );
          })}
        </div>
      </section>
    </>
  );
}
