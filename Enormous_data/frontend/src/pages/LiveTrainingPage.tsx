import {
  Activity,
  CloudSun,
  Database,
  Droplets,
  Gauge,
  GitMerge,
  MonitorCheck,
  RefreshCw,
  ShieldCheck,
  Thermometer,
  TimerReset,
  Wind,
} from 'lucide-react';
import { useMemo } from 'react';
import type { CSSProperties } from 'react';
import {
  useLiveTrainingForecastImpact,
  useLiveTrainingImpact,
  useLiveTrainingMetrics,
  useLiveTrainingRefresh,
  useLiveTrainingStatus,
  useLiveWeatherCurrent,
  useLiveWeatherForecast,
  useLiveWeatherSummary,
} from '../api/hooks';
import { ChartPanel, type DashboardChartOption } from '../components/ChartPanel';
import { MetricCard } from '../components/MetricCard';
import type { LiveTrainingMetricRow, LiveWeatherForecastImpactRow, LiveWeatherImpactItem, NamedValue } from '../types/api';

function number(value?: number | null, digits = 0) {
  if (typeof value !== 'number') return '待生成';
  return value.toLocaleString('zh-CN', { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '待生成';
}

function signed(value?: number | null, digits = 2) {
  if (typeof value !== 'number') return '待生成';
  return `${value > 0 ? '+' : ''}${number(value, digits)}`;
}

function clampPercent(value: number) {
  return Math.max(0, Math.min(100, value));
}

function styleVars(vars: Record<string, string>): CSSProperties {
  return vars as CSSProperties;
}

function statusTone(status?: string): 'primary' | 'success' | 'warning' | 'danger' {
  if (status === 'succeeded' || status === 'passed') return 'success';
  if (status === 'running' || status === 'queued' || status === 'needs_review') return 'warning';
  if (status === 'failed') return 'danger';
  return 'primary';
}

function statusLabel(status?: string) {
  if (status === 'succeeded') return '已完成';
  if (status === 'running') return '运行中';
  if (status === 'queued') return '排队中';
  if (status === 'failed') return '失败';
  if (status === 'passed') return '通过';
  if (status === 'needs_review') return '需复核';
  return status || '待生成';
}

function impactRows(rows: LiveWeatherImpactItem[]): NamedValue[] {
  return rows.map((row) => ({ name: row.entity_label, value: Number(row.impact_score.toFixed(2)) }));
}

function modelName(name: string) {
  if (name === 'baseline_history') return '历史基线';
  if (name === 'weather_enhanced') return '天气增强';
  return name;
}

function comparisonOption(rows: LiveTrainingMetricRow[]): DashboardChartOption {
  const models = rows.map((row) => modelName(row.model_name));
  const wapeValues = rows.map((row) => (row.wape == null ? 0 : Number((row.wape * 100).toFixed(2))));
  const maeValues = rows.map((row) => (row.mae == null ? 0 : Number(row.mae.toFixed(2))));
  return {
    textStyle: { fontFamily: 'Inter, "Microsoft YaHei", system-ui, sans-serif', color: '#d8e2ee' },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, textStyle: { color: '#9fb2c8' } },
    grid: [
      { top: 58, right: 36, height: '30%', left: 72 },
      { top: '58%', right: 36, height: '28%', left: 72 },
    ],
    xAxis: [
      {
        type: 'category',
        gridIndex: 0,
        data: models,
        axisLabel: { color: '#8fa2b7' },
        axisLine: { lineStyle: { color: '#26384c' } },
      },
      {
        type: 'category',
        gridIndex: 1,
        data: models,
        axisLabel: { color: '#8fa2b7' },
        axisLine: { lineStyle: { color: '#26384c' } },
      },
    ],
    yAxis: [
      {
        type: 'value',
        name: 'WAPE(%)',
        gridIndex: 0,
        min: 0,
        splitLine: { lineStyle: { color: '#203247' } },
        axisLabel: { color: '#8fa2b7' },
        nameTextStyle: { color: '#8fa2b7' },
      },
      {
        type: 'value',
        name: 'MAE',
        gridIndex: 1,
        min: 0,
        splitLine: { lineStyle: { color: '#203247' } },
        axisLabel: { color: '#8fa2b7' },
        nameTextStyle: { color: '#8fa2b7' },
      },
    ],
    series: [
      {
        name: 'WAPE(%)',
        type: 'bar',
        barMaxWidth: 28,
        xAxisIndex: 0,
        yAxisIndex: 0,
        label: { show: true, position: 'top', color: '#8fe7df', formatter: '{c}%' },
        itemStyle: { color: '#39d0c8', borderRadius: [6, 6, 0, 0] },
        data: wapeValues,
      },
      {
        name: 'MAE',
        type: 'bar',
        barMaxWidth: 28,
        xAxisIndex: 1,
        yAxisIndex: 1,
        label: { show: true, position: 'top', color: '#f8c36a', formatter: '{c}' },
        itemStyle: { color: '#f59e0b', borderRadius: [6, 6, 0, 0] },
        data: maeValues,
      },
    ],
  };
}

function impactOption(rows: NamedValue[]): DashboardChartOption {
  const ordered = [...rows].slice(0, 12).reverse();
  const values = ordered.map((row) => row.value);
  const minValue = Math.min(0, ...values);
  const maxValue = Math.max(0, ...values);
  return {
    textStyle: { fontFamily: 'Inter, "Microsoft YaHei", system-ui, sans-serif', color: '#d8e2ee' },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { top: 24, right: 72, bottom: 36, left: 132 },
    xAxis: {
      type: 'value',
      min: Math.floor(minValue * 1.08),
      max: Math.ceil(maxValue * 1.08),
      splitLine: { lineStyle: { color: '#203247' } },
      axisLabel: { color: '#8fa2b7' },
    },
    yAxis: {
      type: 'category',
      data: ordered.map((row) => row.name),
      axisLabel: { color: '#8fa2b7', width: 118, overflow: 'truncate' },
      axisLine: { lineStyle: { color: '#26384c' } },
    },
    series: [
      {
        name: '天气影响评分',
        type: 'bar',
        barMaxWidth: 22,
        label: {
          show: true,
          position: 'right',
          color: '#d8e2ee',
          formatter: (params: unknown) => {
            const value = (params as { value?: unknown }).value;
            return signed(typeof value === 'number' ? value : Number(value), 2);
          },
        },
        itemStyle: {
          borderRadius: [0, 6, 6, 0],
          color: (params: unknown) => {
            const rawValue = (params as { value?: unknown }).value;
            const value = typeof rawValue === 'number' ? rawValue : Number(rawValue ?? 0);
            const alpha = Math.max(0.42, Math.min(1, Math.abs(value) / 18));
            return value < 0 ? `rgba(101, 184, 255, ${alpha})` : `rgba(86, 210, 123, ${alpha})`;
          },
        },
        data: ordered.map((row) => row.value),
      },
    ],
  };
}

function forecastImpactOption(rows: LiveWeatherForecastImpactRow[]): DashboardChartOption {
  const chartRows = rows.slice(0, 24);
  return {
    textStyle: { fontFamily: 'Inter, "Microsoft YaHei", system-ui, sans-serif', color: '#d8e2ee' },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { top: 0, textStyle: { color: '#9fb2c8' } },
    grid: { top: 48, right: 68, bottom: 54, left: 68 },
    xAxis: {
      type: 'category',
      data: chartRows.map((row) => String(row.time || '').slice(11, 16)),
      axisLabel: { color: '#8fa2b7' },
      axisLine: { lineStyle: { color: '#26384c' } },
    },
    yAxis: [
      {
        type: 'value',
        name: '影响评分',
        splitLine: { lineStyle: { color: '#203247' } },
        axisLabel: { color: '#8fa2b7' },
        nameTextStyle: { color: '#8fa2b7' },
      },
      {
        type: 'value',
        name: '降水(mm)',
        min: 0,
        splitLine: { show: false },
        axisLabel: { color: '#8fa2b7' },
        nameTextStyle: { color: '#8fa2b7' },
      },
    ],
    series: [
      {
        name: '平均影响',
        type: 'line',
        smooth: true,
        symbolSize: 6,
        itemStyle: { color: '#39d0c8' },
        lineStyle: { color: '#39d0c8', width: 3 },
        data: chartRows.map((row) => row.avg_impact_score),
      },
      {
        name: '最强类目影响',
        type: 'line',
        smooth: true,
        symbolSize: 6,
        itemStyle: { color: '#f59e0b' },
        lineStyle: { color: '#f59e0b', width: 3 },
        data: chartRows.map((row) => row.strongest_impact_score ?? 0),
      },
      {
        name: '降水',
        type: 'bar',
        yAxisIndex: 1,
        barMaxWidth: 12,
        itemStyle: { color: 'rgba(101, 184, 255, 0.38)', borderRadius: [4, 4, 0, 0] },
        data: chartRows.map((row) => row.precipitation ?? 0),
      },
    ],
  };
}

export function LiveTrainingPage() {
  const current = useLiveWeatherCurrent();
  const summary = useLiveWeatherSummary();
  const forecast = useLiveWeatherForecast();
  const status = useLiveTrainingStatus();
  const metrics = useLiveTrainingMetrics();
  const impact = useLiveTrainingImpact();
  const forecastImpact = useLiveTrainingForecastImpact();
  const refresh = useLiveTrainingRefresh();

  const metricOption = useMemo(() => comparisonOption(metrics.data?.model_metrics ?? []), [metrics.data]);
  const liveImpactOption = useMemo(
    () => impactOption(impactRows(impact.data?.items ?? [])),
    [impact.data],
  );
  const futureImpactOption = useMemo(() => forecastImpactOption(forecastImpact.data?.items ?? []), [forecastImpact.data]);
  const hasMissingCache = current.isError || summary.isError || status.isError || metrics.isError || impact.isError || forecastImpact.isError;
  const weather = current.data?.current;
  const topImpact = impact.data?.items?.[0];
  const impactItems = impact.data?.items ?? [];
  const maxAbsImpact = Math.max(1, ...impactItems.map((row) => Math.abs(row.impact_score)));
  const coverage = summary.data?.join_coverage_rate ?? 0;
  const coveragePercent = clampPercent(coverage * 100);
  const wapeLift = metrics.data?.lift.wape_reduction;
  const weatherSource = current.data?.source_status ?? '待拉取';
  const forecastRows = forecastImpact.data?.items ?? [];
  const futureMaxPrecipitation = forecastRows.length ? Math.max(...forecastRows.map((row) => row.precipitation ?? 0)) : null;
  const futureRainHours = forecastRows.filter((row) => (row.precipitation ?? 0) > 0 || (row.rain ?? 0) > 0).length;
  const peakFuture = forecastImpact.data?.summary;
  const trainingBoundary = summary.data?.current_weather_used_for_training ? '需复核' : '已隔离';

  const pipelineSteps = [
    {
      icon: CloudSun,
      label: '实时获取数据',
      title: `${current.data?.city ?? '上海'}天气信号`,
      metric: weather?.temperature_2m == null ? '待生成' : `${number(weather.temperature_2m, 1)}°C`,
      detail: `${weatherSource} · forecast ${forecast.data?.hourly?.length ?? 0}h`,
      tone: weather ? 'cyan' : 'muted',
    },
    {
      icon: GitMerge,
      label: '特征融合',
      title: '2019 电商 x 历史天气',
      metric: percent(summary.data?.join_coverage_rate),
      detail: `${number(summary.data?.joined_rows)} / ${number(summary.data?.ecommerce_agg_rows)} 行完成 join`,
      tone: summary.data?.quality_status === 'passed' ? 'green' : 'amber',
    },
    {
      icon: Activity,
      label: '微批训练/回测',
      title: statusLabel(status.data?.status),
      metric: `${number(status.data?.elapsed_seconds, 1)}s`,
      detail: status.data?.run_id ? `run ${status.data.run_id.slice(0, 12)}` : '等待后台任务',
      tone: status.data?.status === 'failed' ? 'red' : status.data?.status === 'running' ? 'amber' : 'blue',
    },
    {
      icon: Gauge,
      label: '实时推理',
      title: '当前 + 未来24h影响',
      metric: topImpact ? signed(topImpact.impact_score, 1) : '待生成',
      detail: peakFuture?.peak_abs_hour ? `未来峰值 ${peakFuture.peak_abs_hour.slice(11, 16)} · ${peakFuture.peak_abs_category}` : topImpact?.reason ?? '当前天气只进入在线推理',
      tone: topImpact && Math.abs(topImpact.impact_score) > 5 ? 'amber' : 'green',
    },
    {
      icon: MonitorCheck,
      label: '实时渲染',
      title: 'React Query + ECharts',
      metric: '3-10s',
      detail: '状态与当前天气轮询刷新，图表随 cache 更新',
      tone: 'cyan',
    },
  ];

  const telemetryCards = [
    {
      icon: Thermometer,
      label: '温度信号',
      value: weather?.temperature_2m == null ? '待生成' : `${number(weather.temperature_2m, 1)}°C`,
      detail: 'temperature_2m',
      meter: clampPercent(((weather?.temperature_2m ?? 0) + 10) * 1.8),
      tone: 'cyan',
    },
    {
      icon: Droplets,
      label: '湿度信号',
      value: weather?.relative_humidity_2m == null ? '待生成' : `${number(weather.relative_humidity_2m, 0)}%`,
      detail: 'relative_humidity_2m',
      meter: clampPercent(weather?.relative_humidity_2m ?? 0),
      tone: 'blue',
    },
    {
      icon: CloudSun,
      label: '未来24h降雨',
      value: futureMaxPrecipitation == null ? '待生成' : `${number(futureMaxPrecipitation, 2)}mm`,
      detail: `max precipitation · ${futureRainHours || 0}h 有雨`,
      meter: clampPercent((futureMaxPrecipitation ?? 0) * 60),
      tone: 'amber',
    },
    {
      icon: Wind,
      label: '风速信号',
      value: weather?.wind_speed_10m == null ? '待生成' : `${number(weather.wind_speed_10m, 1)}km/h`,
      detail: 'wind_speed_10m',
      meter: clampPercent((weather?.wind_speed_10m ?? 0) * 2.5),
      tone: 'green',
    },
  ];

  const lineageRows = [
    { label: '历史天气源', value: 'archive-api.open-meteo.com/v1/archive', detail: summary.data?.weather_date_range.min ?? '2019 同期' },
    { label: '当前天气源', value: 'api.open-meteo.com/v1/forecast', detail: weather?.time ?? '实时获取' },
    { label: '训练边界', value: '2019 历史天气进入训练', detail: `当前天气：${trainingBoundary}` },
    { label: '渲染数据', value: 'data/cache/live_*.json', detail: 'Flask API + React Query' },
  ];

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">外部信号闭环</span>
        <h1>实时训练与天气影响</h1>
        <p>历史天气只进入 2019 训练/回测；当前天气只用于实时推理和渲染，避免把今天的信号写回历史标签。</p>
      </section>

      {hasMissingCache ? <div className="error-banner">实时天气闭环缓存尚未生成，请点击刷新启动微批训练。</div> : null}

      <section className="live-command-grid">
        <div className="live-orchestration-panel">
          <div className="live-panel-head">
            <div>
              <span className={`status-pill tone-${statusTone(status.data?.status)}`}>{statusLabel(status.data?.status)}</span>
              <h2>实时获取数据 → 特征融合 → 微批训练/回测 → 实时推理 → 实时渲染</h2>
              <p>{metrics.data?.interpretation ?? '等待天气增强训练结果。'}</p>
            </div>
            <button className="primary-action" disabled={refresh.isPending || status.data?.status === 'running'} onClick={() => refresh.mutate()} type="button">
              <RefreshCw size={18} className={refresh.isPending ? 'spin' : ''} />
              {refresh.isPending ? '启动中' : '刷新实时训练'}
            </button>
          </div>
          <ol className="live-evidence-chain" aria-label="实时训练证据链">
            {pipelineSteps.map((step, index) => {
              const Icon = step.icon;
              return (
                <li className={`live-chain-node tone-${step.tone}`} key={step.label}>
                  <span className="live-chain-index">{String(index + 1).padStart(2, '0')}</span>
                  <Icon size={20} />
                  <small>{step.label}</small>
                  <strong>{step.metric}</strong>
                  <span>{step.title}</span>
                  <em>{step.detail}</em>
                </li>
              );
            })}
          </ol>
        </div>

        <aside className="live-proof-panel" aria-label="时间穿越隔离证明">
          <div className="live-proof-lock">
            <ShieldCheck size={24} />
            <span>时间穿越隔离证明</span>
          </div>
          <div className="live-proof-lanes">
            <div>
              <small>历史训练/回测</small>
              <strong>{summary.data?.ecommerce_date_range.min ?? '2019-10-01'} 至 {summary.data?.ecommerce_date_range.max ?? '2019-11-30'}</strong>
              <span>只 join 2019 同期历史天气</span>
            </div>
            <div>
              <small>实时推理/渲染</small>
              <strong>{weather?.time ?? '等待当前天气'}</strong>
              <span>当前天气不回写训练标签</span>
            </div>
          </div>
          <div className={`live-boundary-badge ${summary.data?.current_weather_used_for_training ? 'is-warning' : 'is-ok'}`}>
            {summary.data?.current_weather_used_for_training ? '当前天气进入训练，需复核' : '当前天气仅用于在线推理'}
          </div>
        </aside>
      </section>

      <section className="live-telemetry-grid" aria-label="当前天气实时遥测">
        {telemetryCards.map((card) => {
          const Icon = card.icon;
          return (
            <article className={`live-signal-card tone-${card.tone}`} key={card.label}>
              <div>
                <Icon size={20} />
                <span>{card.label}</span>
              </div>
              <strong>{card.value}</strong>
              <small>{card.detail}</small>
              <div className="live-signal-meter" style={styleVars({ '--signal': `${card.meter}%` })}>
                <span />
              </div>
            </article>
          );
        })}
      </section>

      <section className="live-evidence-grid">
        <article className="live-evidence-card live-coverage-card">
          <div className="panel-title">
            <div>
              <h2>特征融合质量</h2>
              <p>历史天气与电商日聚合 join 覆盖率。</p>
            </div>
            <GitMerge size={20} />
          </div>
          <div className="live-coverage-ring" style={styleVars({ '--coverage': `${coveragePercent}%` })}>
            <span>{percent(summary.data?.join_coverage_rate)}</span>
            <small>join coverage</small>
          </div>
          <div className="live-card-stats">
            <span>weather rows <strong>{number(summary.data?.weather_rows)}</strong></span>
            <span>joined rows <strong>{number(summary.data?.joined_rows)}</strong></span>
            <span>missing rate <strong>{percent(summary.data?.missing_weather_rate)}</strong></span>
          </div>
        </article>

        <article className="live-evidence-card live-model-card">
          <div className="panel-title">
            <div>
              <h2>回测对比</h2>
              <p>baseline 与 weather-enhanced 的真实指标差异。</p>
            </div>
            <Gauge size={20} />
          </div>
          <div className="live-model-delta">
            <span>{metrics.data?.comparison_status === 'improved' ? '有提升' : '无显著提升'}</span>
            <strong>{wapeLift == null ? '待生成' : `${signed(wapeLift * 100, 2)}%`}</strong>
            <small>WAPE reduction</small>
          </div>
          <div className="live-model-lanes">
            {(metrics.data?.model_metrics ?? []).map((row) => (
              <div key={row.model_name}>
                <span>{modelName(row.model_name)}</span>
                <strong>{row.wape == null ? '待生成' : `${number(row.wape * 100, 2)}%`}</strong>
                <em>MAE {number(row.mae, 2)}</em>
              </div>
            ))}
          </div>
        </article>

        <article className="live-evidence-card live-lineage-card">
          <div className="panel-title">
            <div>
              <h2>数据血缘</h2>
              <p>从外部 API 到前端渲染的关键证据。</p>
            </div>
            <Database size={20} />
          </div>
          <div className="live-lineage-list">
            {lineageRows.map((row) => (
              <div key={row.label}>
                <span>{row.label}</span>
                <strong>{row.value}</strong>
                <small>{row.detail}</small>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="metric-grid live-compact-metrics">
        <MetricCard detail={`${current.data?.city ?? '上海'} · ${weatherSource}`} label="当前温度" tone="primary" value={weather?.temperature_2m == null ? '待生成' : `${number(weather.temperature_2m, 1)}°C`} />
        <MetricCard detail="历史天气与 2019 电商日聚合 join" label="Join 覆盖率" tone={summary.data?.quality_status === 'passed' ? 'success' : 'warning'} value={percent(summary.data?.join_coverage_rate)} />
        <MetricCard detail={`${status.data?.run_id?.slice(0, 12) ?? '暂无 run'} · ${number(status.data?.elapsed_seconds, 1)}s`} label="训练状态" tone={statusTone(status.data?.status)} value={statusLabel(status.data?.status)} />
        <MetricCard detail={topImpact?.reason ?? '等待当前天气推理'} label="最强影响" tone={topImpact && Math.abs(topImpact.impact_score) > 5 ? 'warning' : 'success'} value={topImpact ? `${topImpact.entity_label} ${signed(topImpact.impact_score, 1)}` : '待生成'} />
      </section>

      <section className="chart-grid two-column">
        <ChartPanel
          chartId="live-training-metrics"
          isEmpty={!metrics.data?.model_metrics?.length}
          option={metricOption}
          subtitle="展示历史基线与天气增强模型的 WAPE/MAE；若未提升，会明确标记为解释性增强。"
          summary={`WAPE 降低：${metrics.data?.lift.wape_reduction == null ? '待生成' : (metrics.data.lift.wape_reduction * 100).toFixed(2) + '%'}`}
          title="Baseline vs Weather-enhanced"
        />
        <ChartPanel
          chartId="live-weather-impact"
          isEmpty={!impact.data?.items?.length}
          option={liveImpactOption}
          subtitle="当前天气不参与历史训练，只根据训练期天气响应分布生成实时类目影响评分。"
          summary={`当前天气时间：${impact.data?.current_weather_time ?? weather?.time ?? '待生成'}`}
          title="实时业务影响评分"
        />
      </section>

      <section className="data-panel live-forecast-panel">
        <div className="panel-title">
          <div>
            <h2>未来 24 小时影响曲线</h2>
            <p>Open-Meteo hourly forecast 只用于在线推理，展示未来天气变化对类目需求的逐小时影响。</p>
          </div>
          <CloudSun size={20} />
        </div>
        <div className="live-forecast-summary">
          <div>
            <span>预测窗口</span>
            <strong>{forecastImpact.data?.forecast_weather_time_range.min ?? '待生成'} 至 {forecastImpact.data?.forecast_weather_time_range.max ?? '待生成'}</strong>
          </div>
          <div>
            <span>影响峰值</span>
            <strong>{peakFuture?.peak_abs_hour ?? '待生成'} · {peakFuture?.peak_abs_category ?? '待生成'} {signed(peakFuture?.peak_abs_impact_score, 2)}</strong>
          </div>
          <div>
            <span>主导天气因子</span>
            <strong>{peakFuture?.dominant_driver ?? '待生成'}</strong>
          </div>
          <div>
            <span>训练边界</span>
            <strong>{forecastImpact.data?.training_uses_forecast_weather ? '预测天气进入训练' : '预测天气仅在线推理'}</strong>
          </div>
        </div>
        <ChartPanel
          chartId="live-weather-forecast-impact"
          isEmpty={!forecastRows.length}
          option={futureImpactOption}
          subtitle="平均影响、最强类目影响和降水量按小时联动展示。"
          summary={`窗口：${forecast.data?.forecast_window_start ?? forecastImpact.data?.forecast_weather_time_range.min ?? '待生成'} -> ${forecast.data?.forecast_window_end ?? forecastImpact.data?.forecast_weather_time_range.max ?? '待生成'} · rows：${forecastRows.length || '待生成'}`}
          title="未来 24h forecast impact"
        />
        <table className="data-table live-forecast-table" aria-label="未来24小时影响清单">
          <thead>
            <tr>
              <th>时间</th>
              <th>温度</th>
              <th>降水</th>
              <th>平均影响</th>
              <th>最强类目</th>
              <th>最强影响</th>
            </tr>
          </thead>
          <tbody>
            {forecastRows.slice(0, 8).map((row) => (
              <tr key={row.time}>
                <td>{row.time}</td>
                <td>{number(row.temperature_2m, 1)}°C</td>
                <td>{number(row.precipitation, 2)}mm</td>
                <td>{signed(row.avg_impact_score, 2)}</td>
                <td>{row.strongest_category ?? '待生成'}</td>
                <td>{signed(row.strongest_impact_score, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="data-panel">
        <div className="panel-title">
          <div>
            <h2>证据链明细</h2>
            <p>保留历史范围、天气范围、质量门禁和当前天气使用边界。</p>
          </div>
          <ShieldCheck size={20} />
        </div>
        <div className="quality-grid">
          <div><span>电商时间范围</span><strong>{summary.data?.ecommerce_date_range.min ?? '待生成'} 至 {summary.data?.ecommerce_date_range.max ?? '待生成'}</strong></div>
          <div><span>天气时间范围</span><strong>{summary.data?.weather_date_range.min ?? '待生成'} 至 {summary.data?.weather_date_range.max ?? '待生成'}</strong></div>
          <div><span>当前天气训练用途</span><strong>{summary.data?.current_weather_used_for_training ? '已进入训练' : '仅实时推理'}</strong></div>
          <div><span>样本行</span><strong>{number(summary.data?.joined_rows)} / {number(summary.data?.ecommerce_agg_rows)}</strong></div>
        </div>
      </section>

      <section className="data-panel">
        <div className="panel-title">
          <div>
            <h2>类目影响清单</h2>
            <p>推荐权重仅作为当前天气场景下的解释性调整建议。</p>
          </div>
          <CloudSun size={20} />
        </div>
        <table className="data-table" aria-label="天气影响清单">
          <thead>
            <tr>
              <th>类目</th>
              <th>影响评分</th>
              <th>需求倍率</th>
              <th>推荐权重</th>
              <th>解释</th>
            </tr>
          </thead>
          <tbody>
            {impactItems.map((row) => (
              <tr key={row.entity_key}>
                <td>{row.entity_label}</td>
                <td>
                  <div className={`impact-score-cell ${row.impact_score >= 0 ? 'is-positive' : 'is-negative'}`}>
                    <strong>{signed(row.impact_score, 2)}</strong>
                    <span className="impact-score-meter" style={styleVars({ '--impact': `${clampPercent((Math.abs(row.impact_score) / maxAbsImpact) * 100)}%` })} />
                  </div>
                </td>
                <td>{number(row.demand_multiplier, 3)}</td>
                <td>{number(row.recommendation_weight, 3)}</td>
                <td>{row.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="ops-command-band live-boundary-band">
        <div>
          <span className={`status-pill tone-${metrics.data?.lift.improved ? 'success' : 'warning'}`}>
            {metrics.data?.comparison_status === 'improved' ? '有提升' : '无显著提升'}
          </span>
          <h2>时间穿越防护</h2>
          <p>2019 历史天气用于训练和回测；当前天气仅进入在线影响评分，不回写历史训练标签。</p>
        </div>
        <TimerReset size={22} />
      </section>
    </>
  );
}
