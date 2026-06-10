import { useEffect, useId, useRef } from 'react';
import { BarChart, LineChart, PieChart } from 'echarts/charts';
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
  type GridComponentOption,
  type LegendComponentOption,
  type TooltipComponentOption,
} from 'echarts/components';
import * as echarts from 'echarts/core';
import type { ComposeOption } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import type { BarSeriesOption, LineSeriesOption, PieSeriesOption } from 'echarts/charts';

echarts.use([BarChart, LineChart, PieChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

export type DashboardChartOption = ComposeOption<
  | BarSeriesOption
  | LineSeriesOption
  | PieSeriesOption
  | GridComponentOption
  | LegendComponentOption
  | TooltipComponentOption
>;

type ChartPanelProps = {
  title: string;
  subtitle: string;
  option: DashboardChartOption;
  summary?: string;
};

export function ChartPanel({ title, subtitle, option, summary }: ChartPanelProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const summaryId = useId();

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption(option, true);
    const resize = () => chart.resize();
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('resize', resize);
      chart.dispose();
    };
  }, [option]);

  return (
    <section className="data-panel chart-panel">
      <div className="panel-title">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </div>
      <div
        ref={ref}
        aria-describedby={summary ? summaryId : undefined}
        aria-label={`${title}：${summary ?? subtitle}`}
        className="chart-canvas"
        role="img"
        tabIndex={0}
      />
      {summary ? (
        <p className="chart-summary" id={summaryId}>
          {summary}
        </p>
      ) : null}
    </section>
  );
}
