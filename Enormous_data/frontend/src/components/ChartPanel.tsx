import { useEffect, useId, useRef } from 'react';
import type { ReactNode } from 'react';
import { BarChart, CustomChart, GraphChart, HeatmapChart, LineChart, PieChart, SankeyChart, ScatterChart } from 'echarts/charts';
import {
  AriaComponent,
  AxisPointerComponent,
  CalendarComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  VisualMapComponent,
  type AriaComponentOption,
  type AxisPointerComponentOption,
  type CalendarComponentOption,
  type DataZoomComponentOption,
  type GridComponentOption,
  type LegendComponentOption,
  type TooltipComponentOption,
  type VisualMapComponentOption,
} from 'echarts/components';
import * as echarts from 'echarts/core';
import type { ComposeOption, ECElementEvent } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import type {
  BarSeriesOption,
  CustomSeriesOption,
  GraphSeriesOption,
  HeatmapSeriesOption,
  LineSeriesOption,
  PieSeriesOption,
  SankeySeriesOption,
  ScatterSeriesOption,
} from 'echarts/charts';
import { ChartEmptyState } from './ChartEmptyState';

echarts.use([
  BarChart,
  CustomChart,
  GraphChart,
  HeatmapChart,
  LineChart,
  PieChart,
  SankeyChart,
  ScatterChart,
  AriaComponent,
  CalendarComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  DataZoomComponent,
  AxisPointerComponent,
  VisualMapComponent,
  CanvasRenderer,
]);

export type DashboardChartOption = ComposeOption<
  | BarSeriesOption
  | CustomSeriesOption
  | GraphSeriesOption
  | HeatmapSeriesOption
  | LineSeriesOption
  | PieSeriesOption
  | SankeySeriesOption
  | ScatterSeriesOption
  | AriaComponentOption
  | CalendarComponentOption
  | GridComponentOption
  | LegendComponentOption
  | TooltipComponentOption
  | DataZoomComponentOption
  | AxisPointerComponentOption
  | VisualMapComponentOption
>;

type ChartPanelProps = {
  title: string;
  subtitle: string;
  option: DashboardChartOption;
  summary?: string;
  /** ECharts group name — charts in the same group sync tooltip/legend/dataZoom */
  group?: string;
  /** Stable chart id used in cross-filter evidence and tests */
  chartId?: string;
  /** Short localized statement explaining the current filter/evidence state */
  filterNotice?: string;
  /** Compact evidence badges, usually annotation or provenance labels */
  annotations?: Array<{ label: string; value?: string; tone?: 'info' | 'success' | 'warning' | 'danger' }>;
  /** Default-collapsed technical evidence for filtered or annotated charts */
  evidence?: ReactNode;
  /** Click event handler for cross-chart filtering */
  onChartClick?: (params: ECElementEvent) => void;
  isLoading?: boolean;
  error?: Error | null;
  isEmpty?: boolean;
  emptyText?: string;
  actionHint?: string;
  actions?: ReactNode;
};

export function ChartPanel({
  title,
  subtitle,
  option,
  summary,
  group,
  chartId,
  filterNotice,
  annotations = [],
  evidence,
  onChartClick,
  isLoading = false,
  error,
  isEmpty = false,
  emptyText,
  actionHint,
  actions,
}: ChartPanelProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const summaryId = useId();
  const hasPanelState = isLoading || Boolean(error) || isEmpty;

  useEffect(() => {
    if (hasPanelState) {
      chartRef.current?.dispose();
      chartRef.current = null;
      return;
    }
    if (!ref.current) return;
    if (import.meta.env.MODE === 'test') return;

    let chart = chartRef.current;
    if (!chart) {
      chart = echarts.init(ref.current);
      chartRef.current = chart;
    }

    chart.setOption(option, { notMerge: true, lazyUpdate: true });

    if (group) {
      chart.group = group;
    }

    if (onChartClick) {
      chart.on('click', onChartClick);
    }

    const resize = () => chart!.resize();
    window.addEventListener('resize', resize);

    return () => {
      window.removeEventListener('resize', resize);
      if (onChartClick) {
        chart!.off('click', onChartClick);
      }
    };
  }, [option, group, onChartClick, hasPanelState]);

  useEffect(() => {
    return () => {
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  return (
    <section className="data-panel chart-panel">
      <div className="panel-title">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </div>
      {hasPanelState ? (
        <ChartEmptyState
          actionHint={actionHint}
          description={error ? '图表数据暂时无法加载。' : emptyText}
          title={isLoading ? '正在加载图表' : error ? '图表加载失败' : '暂无图表数据'}
          tone={isLoading ? 'loading' : error ? 'error' : 'empty'}
        />
      ) : (
        <div
          ref={ref}
          aria-describedby={summary ? summaryId : undefined}
          aria-label={`${title}：${[summary ?? subtitle, filterNotice, annotations.map((item) => `${item.label}${item.value ? `：${item.value}` : ''}`).join('，')].filter(Boolean).join('；')}`}
          data-chart-id={chartId}
          className="chart-canvas"
          role="img"
          tabIndex={0}
        />
      )}
      {filterNotice ? <p className="chart-filter-notice">{filterNotice}</p> : null}
      {annotations.length ? (
        <div className="chart-annotation-badges" aria-label={`${title}图表标注`}>
          {annotations.map((item) => (
            <span className={`tone-${item.tone ?? 'info'}`} key={`${item.label}-${item.value ?? ''}`}>
              {item.label}
              {item.value ? <small>{item.value}</small> : null}
            </span>
          ))}
        </div>
      ) : null}
      {summary ? (
        <p className="chart-summary" id={summaryId}>
          {summary}
        </p>
      ) : null}
      {evidence ? (
        <details className="chart-evidence">
          <summary>查看筛选证据</summary>
          {evidence}
        </details>
      ) : null}
      {actions ? <div className="chart-actions">{actions}</div> : null}
    </section>
  );
}
