import { useState } from 'react';
import { AlertTriangle, BellRing, Crosshair, Radar, ShieldCheck } from 'lucide-react';
import {
  useAnomalyAlerts,
  useAnomalyEvaluation,
  useAnomalyIncidents,
  useAnomalyRootCause,
  useAnomalyRules,
  useAnomalySummary,
  useAnomalyTimeline,
} from '../api/hooks';
import { ChartPanel, type DashboardChartOption } from '../components/ChartPanel';
import { algorithmCopy, displayValue, fieldLabel, label, statusLabel } from '../i18n/displayText';
import { donutOption } from '../lib/chartOptions';
import type { AnomalyAlert, AnomalyRootCause, AnomalyTimelinePoint, NamedValue } from '../types/api';

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : '待生成';
}

function score(value?: number | null) {
  return typeof value === 'number' ? value.toFixed(2) : '待生成';
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '待生成';
}

function statusTone(status?: string) {
  if (status === 'healthy' || status === 'passed') return 'success';
  if (status === 'critical' || status === 'failed') return 'failed';
  return 'queued';
}

function metricTone(count?: number | null, warning = false) {
  if (!count) return '';
  return warning ? 'tone-warning' : 'tone-danger';
}

function shortLabel(value: string) {
  return value.length > 20 ? `${value.slice(0, 18)}...` : value;
}

function rootCauseRows(rows: AnomalyRootCause[]): NamedValue[] {
  return rows
    .slice()
    .sort((a, b) => Math.abs(b.contribution_share) - Math.abs(a.contribution_share))
    .slice(0, 10)
    .map((row) => ({
      name: shortLabel(`${label('entityType', row.dimension, { fallback: row.dimension })} · ${displayValue(row.value)}`),
      value: Number((Math.abs(row.contribution_share) * 100).toFixed(1)),
    }));
}

function anomalyCalendarOption(rows: AnomalyTimelinePoint[]): DashboardChartOption {
  const ordered = rows.slice().sort((a, b) => a.dt.localeCompare(b.dt));
  const values = ordered.map((row) => [row.dt, row.critical_count * 3 + row.warning_count * 2 + row.watch_count]);
  const maxValue = Math.max(1, ...values.map((item) => Number(item[1]) || 0));
  const range = ordered.length ? [ordered[0].dt, ordered[ordered.length - 1].dt] : undefined;

  return {
    textStyle: {
      fontFamily: 'Inter, "Microsoft YaHei", system-ui, sans-serif',
      color: '#d8e2ee',
    },
    aria: {
      show: true,
      label: { description: '异常日历热力图，按日期展示严重、警告和观察信号的加权强度。' },
    },
    tooltip: {
      trigger: 'item',
      formatter: (params: unknown) => {
        const data = (params as { data?: [string, number] }).data;
        if (!data) return '暂无异常信号';
        const row = ordered.find((item) => item.dt === data[0]);
        return [
          `${data[0]}`,
          `严重：${number(row?.critical_count)}`,
          `警告：${number(row?.warning_count)}`,
          `观察：${number(row?.watch_count)}`,
          `最大稳健分数：${score(row?.max_robust_z)}`,
        ].join('<br/>');
      },
    },
    visualMap: {
      min: 0,
      max: maxValue,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#17324a', '#f59e0b', '#fb7185'] },
      textStyle: { color: '#9fb2c8' },
    },
    calendar: {
      top: 28,
      left: 40,
      right: 24,
      bottom: 44,
      range,
      cellSize: ['auto', 18],
      itemStyle: { borderWidth: 1, borderColor: '#17283d' },
      yearLabel: { show: false },
      monthLabel: { color: '#9fb2c8' },
      dayLabel: { color: '#9fb2c8', firstDay: 1, nameMap: ['日', '一', '二', '三', '四', '五', '六'] },
    },
    series: [
      {
        name: '异常强度',
        type: 'heatmap',
        coordinateSystem: 'calendar',
        data: values,
      },
    ],
  } as DashboardChartOption;
}

function baselineBandOption(alerts: AnomalyAlert[]): DashboardChartOption {
  const rows = alerts
    .filter((row) => row.dt && typeof row.actual === 'number' && typeof row.baseline === 'number')
    .slice()
    .sort((a, b) => String(a.dt).localeCompare(String(b.dt)))
    .slice(0, 30);
  const axis = rows.map((row) => row.dt ?? '');
  const actual = rows.map((row) => Number(row.actual ?? 0));
  const baseline = rows.map((row) => Number(row.baseline ?? 0));
  const upper = rows.map((row) => {
    const base = Number(row.baseline ?? 0);
    const delta = Math.abs(Number(row.delta ?? 0));
    return Number((base + delta).toFixed(2));
  });
  const lower = rows.map((row) => {
    const base = Number(row.baseline ?? 0);
    const delta = Math.abs(Number(row.delta ?? 0));
    return Number(Math.max(0, base - delta).toFixed(2));
  });

  return {
    textStyle: {
      fontFamily: 'Inter, "Microsoft YaHei", system-ui, sans-serif',
      color: '#d8e2ee',
    },
    aria: {
      show: true,
      label: { description: '异常实际值与基线带图，展示告警日期的实际值、基线和上下界。' },
    },
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { color: '#9fb2c8' } },
    grid: { top: 52, right: 24, bottom: 42, left: 72 },
    xAxis: {
      type: 'category',
      data: axis,
      axisLabel: { color: '#8fa2b7' },
      axisLine: { lineStyle: { color: '#26384c' } },
    },
    yAxis: {
      type: 'value',
      scale: true,
      splitLine: { lineStyle: { color: '#203247' } },
      axisLabel: { color: '#8fa2b7' },
    },
    series: [
      {
        name: '实际值',
        type: 'line',
        data: actual,
        symbolSize: 7,
        showAllSymbol: true,
        lineStyle: { width: 3, color: '#fb7185' },
      },
      {
        name: '基线',
        type: 'line',
        data: baseline,
        symbolSize: 5,
        showAllSymbol: true,
        lineStyle: { width: 2, color: '#39d0c8' },
      },
      {
        name: '上界',
        type: 'line',
        data: upper,
        symbol: 'none',
        showAllSymbol: true,
        lineStyle: { width: 1, color: '#64748b', type: 'dashed' },
      },
      {
        name: '下界',
        type: 'line',
        data: lower,
        symbol: 'none',
        showAllSymbol: true,
        lineStyle: { width: 1, color: '#64748b', type: 'dashed' },
      },
    ],
  } as DashboardChartOption;
}

function rootCauseWaterfallOption(rows: NamedValue[]): DashboardChartOption {
  const visible = rows.slice(0, 8);
  let running = 0;
  const offset: number[] = [];
  const contribution: number[] = [];
  visible.forEach((row) => {
    offset.push(running);
    contribution.push(row.value);
    running += row.value;
  });

  return {
    textStyle: {
      fontFamily: 'Inter, "Microsoft YaHei", system-ui, sans-serif',
      color: '#d8e2ee',
    },
    aria: {
      show: true,
      label: { description: '根因贡献瀑布图，展示各维度贡献如何累积成主要异常影响。' },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: unknown) => {
        const series = Array.isArray(params) ? params as Array<{ seriesName: string; name: string; value: number }> : [];
        const item = series.find((entry) => entry.seriesName === '贡献占比');
        return item ? `${item.name}<br/>贡献占比：${Number(item.value).toFixed(1)}%` : '';
      },
    },
    grid: { top: 24, right: 24, bottom: 72, left: 56 },
    xAxis: {
      type: 'category',
      data: visible.map((row) => row.name),
      axisLabel: { color: '#8fa2b7', rotate: 25 },
      axisLine: { lineStyle: { color: '#26384c' } },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#203247' } },
      axisLabel: { color: '#8fa2b7' },
    },
    series: [
      {
        name: '累计基线',
        type: 'bar',
        stack: 'total',
        itemStyle: { color: 'transparent', borderColor: 'transparent' },
        emphasis: { itemStyle: { color: 'transparent', borderColor: 'transparent' } },
        data: offset,
      },
      {
        name: '贡献占比',
        type: 'bar',
        stack: 'total',
        itemStyle: { color: '#65b8ff' },
        data: contribution,
      },
    ],
  } as DashboardChartOption;
}

export function AnomalyPage() {
  const summary = useAnomalySummary();
  const alerts = useAnomalyAlerts(80);
  const incidents = useAnomalyIncidents(50);
  const topIncidentId = incidents.data?.[0]?.incident_id;
  const rootCause = useAnomalyRootCause({ incident_id: topIncidentId });
  const evaluation = useAnomalyEvaluation();
  const timeline = useAnomalyTimeline();
  const rules = useAnomalyRules();
  const hasError =
    summary.isError ||
    alerts.isError ||
    timeline.isError ||
    rules.isError;
  const causeRows = rootCauseRows(rootCause.data ?? []);
  const alertRows = alerts.data ?? [];
  // 仅保留真实触发严重（critical）或警告（warning）的警报行，用于表格明细和详情卡片的默认选择展示
  const activeAlertRows = alertRows.filter(
    (a) => a.severity === 'critical' || a.severity === 'warning'
  );
  const latestTimeline = (timeline.data ?? []).slice().sort((a, b) => a.dt.localeCompare(b.dt)).at(-1);

  // 状态绑定：保存用户当前点击/选中的具体告警行
  const [selectedAlert, setSelectedAlert] = useState<AnomalyAlert | null>(null);
  // 若未手动选择，则默认采用真实告警列表中最高优先级的告警（评分排序排首位）
  const activeAlert = selectedAlert || activeAlertRows[0];

  // 筛选出与 activeAlert 属于同一实体且属于同一指标的告警点集合
  const filteredBandRows = alertRows.filter(
    (row) =>
      activeAlert &&
      row.entity_id === activeAlert.entity_id &&
      row.entity_type === activeAlert.entity_type &&
      row.metric === activeAlert.metric &&
      row.dt &&
      typeof row.actual === 'number' &&
      typeof row.baseline === 'number'
  );

  const seasonalSignals = evaluation.data?.baseline.seasonal_signal_count ?? 0;
  const totalSignals = evaluation.data?.alert_budget.signal_count ?? 0;
  const baselineRows = [
    { name: '星期季节性基线', value: seasonalSignals },
    { name: '全局稳健基线', value: Math.max(0, totalSignals - seasonalSignals) },
  ].filter((row) => row.value > 0);

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">异常监控</span>
        <h1>运营异常雷达</h1>
        <p>基于特征集市的日级商品和类目信号，用星期季节性基线与稳健分数识别收入、转化和流量异常。</p>
      </section>

      {hasError ? (
        <div className="error-banner" role="alert">
          异常雷达缓存尚未生成，请先运行 Spark 刷新任务。
        </div>
      ) : null}

      <section className="ops-command-band">
        <div>
          <span aria-label={`雷达状态：${statusLabel(summary.data?.radar_status)}`} className={`status-pill tone-${statusTone(summary.data?.radar_status)}`}>
            {statusLabel(summary.data?.radar_status)}
          </span>
          <h2>{summary.data?.contract_version ? '异常雷达契约 v1' : '等待异常雷达契约'}</h2>
          <p>
            {summary.data?.run_id ?? '等待异常雷达'} · {summary.data?.date_range.min_dt ?? '待生成'} 至{' '}
            {summary.data?.date_range.max_dt ?? '待生成'}
          </p>
        </div>
        <Radar size={22} />
      </section>

      <section className="metrics-strip">
        <article className={`metric-card ${metricTone(summary.data?.critical_count)}`}>
          <span>严重异常</span>
          <strong>{number(summary.data?.critical_count)}</strong>
          <small>{number(summary.data?.alert_count)} 条总告警</small>
        </article>
        <article className={`metric-card ${metricTone(summary.data?.warning_count, true)}`}>
          <span>警告异常</span>
          <strong>{number(summary.data?.warning_count)}</strong>
          <small>{number(summary.data?.watch_count)} 条观察信号</small>
        </article>
        <article className="metric-card">
          <span>监控实体</span>
          <strong>{number(summary.data?.monitored_entities)}</strong>
          <small>{number(summary.data?.signal_count)} 条日级信号</small>
        </article>
        <article className="metric-card">
          <span>最大稳健分数</span>
          <strong>{score(summary.data?.max_robust_z)}</strong>
          <small>{number(summary.data?.monitored_days)} 个监控日</small>
        </article>
      </section>

      <section className="content-grid visual-first-grid">
        <ChartPanel
          title="异常日历热力图"
          subtitle="按日期展示严重、警告和观察信号的加权强度"
          option={anomalyCalendarOption(timeline.data ?? [])}
          isEmpty={!timeline.data?.length}
          summary={latestTimeline ? `${latestTimeline.dt} 异常信号数为 ${number(latestTimeline.critical_count + latestTimeline.warning_count + latestTimeline.watch_count)}。` : '等待异常时间线。'}
        />
        <ChartPanel
          title="实际值与基线带"
          subtitle="对比告警日期的实际值、稳健基线和偏移范围"
          option={baselineBandOption(filteredBandRows)}
          isEmpty={!filteredBandRows.length}
          summary={activeAlert ? `${displayValue(activeAlert.entity_label)} 的 ${fieldLabel(activeAlert.metric)} 偏离基线。` : '等待告警基线数据。'}
        />
        <ChartPanel
          title="基线覆盖结构"
          subtitle="区分星期季节性基线和全局稳健兜底基线"
          option={donutOption(baselineRows, '基线信号数')}
          isEmpty={!baselineRows.length}
          summary={`星期季节性覆盖率 ${percent(evaluation.data?.baseline.seasonal_coverage_rate)}。`}
        />
        <ChartPanel
          title="根因贡献瀑布图"
          subtitle="用累计贡献解释异常主要由哪些维度推动"
          option={rootCauseWaterfallOption(causeRows)}
          isEmpty={!causeRows.length}
          summary={causeRows[0] ? `${causeRows[0].name} 贡献占比最高，为 ${causeRows[0].value.toFixed(1)}%。` : '等待根因贡献。'}
        />
      </section>

      <section className="ops-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>{selectedAlert ? '选中异常详情' : '最高优先级异常'}</h2>
              <p>{selectedAlert ? '在下方告警明细中点击任意行可查看其他实体详情。' : '当前最需关注的异动对象，在下方明细点击行可切换。'}</p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {selectedAlert && (
                <button
                  onClick={() => setSelectedAlert(null)}
                  style={{
                    fontSize: '12px',
                    padding: '4px 8px',
                    backgroundColor: 'rgba(57, 208, 200, 0.15)',
                    color: '#39d0c8',
                    border: '1px solid #39d0c8',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  重置为最高优先级
                </button>
              )}
              <BellRing size={20} />
            </div>
          </div>
          {activeAlert ? (
            <dl>
              <dt>告警类型</dt>
              <dd>{fieldLabel(activeAlert.alert_code)}</dd>
              <dt>影响对象</dt>
              <dd>{activeAlert.entity_label}</dd>
              <dt>指标</dt>
              <dd>{fieldLabel(activeAlert.metric)}</dd>
              <dt>方向</dt>
              <dd>{label('direction', activeAlert.direction)}</dd>
              <dt>基线模式</dt>
              <dd>{activeAlert.baseline_mode ? label('model', activeAlert.baseline_mode) : '待生成'}</dd>
              <dt>建议动作</dt>
              <dd>{algorithmCopy(activeAlert.recommended_action)}</dd>
            </dl>
          ) : (
            <p className="empty-copy">当前没有异常告警。</p>
          )}
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>规则与评估门禁</h2>
              <p>{rules.data?.baseline ? algorithmCopy(rules.data.baseline) : '等待规则报告'}</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <div className="quality-checks">
            {(rules.data?.rules ?? []).map((rule) => (
              <div className="quality-check tone-success" key={rule.name}>
                <Crosshair size={16} />
                <span>{fieldLabel(rule.name)}</span>
                <strong>{score(rule.threshold)}</strong>
              </div>
            ))}
            {(evaluation.data?.quality_gates ?? []).map((check) => (
              <div className={`quality-check tone-${check.passed ? 'success' : 'danger'}`} key={check.name}>
                <span>{fieldLabel(check.name)}</span>
                <strong>{String(check.actual)} {check.operator} {String(check.expected)}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>

      <details className="detail-table-disclosure">
        <summary>查看异常时间线明细</summary>
        <section className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>异常时间线</h2>
              <p>按日聚合的异常信号强度。</p>
            </div>
            <AlertTriangle size={20} />
          </div>
          <div className="table-scroll">
            <table aria-label="异常时间线">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>信号数</th>
                  <th>严重数</th>
                  <th>警告数</th>
                  <th>观察数</th>
                  <th>最大稳健分数</th>
                </tr>
              </thead>
              <tbody>
                {(timeline.data ?? []).map((row) => (
                  <tr key={row.dt}>
                    <td>{row.dt}</td>
                    <td>{number(row.signal_count)}</td>
                    <td>{number(row.critical_count)}</td>
                    <td>{number(row.warning_count)}</td>
                    <td>{number(row.watch_count)}</td>
                    <td>{score(row.max_robust_z)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </details>

      <details className="detail-table-disclosure">
        <summary>查看告警证据明细</summary>
        <section className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>告警证据</h2>
              <p>保留实际值、基线、偏移和建议动作，便于复盘。</p>
            </div>
          </div>
          <div className="table-scroll">
            <table aria-label="异常告警证据">
              <thead>
                <tr>
                  <th>等级</th>
                  <th>日期</th>
                  <th>对象</th>
                  <th>对象类型</th>
                  <th>指标</th>
                  <th>方向</th>
                  <th>实际</th>
                  <th>基线</th>
                  <th>偏移</th>
                  <th>稳健分数</th>
                  <th>建议动作</th>
                </tr>
              </thead>
              <tbody>
                {activeAlertRows.map((alert, index) => {
                  const isSelected = activeAlert &&
                    alert.entity_id === activeAlert.entity_id &&
                    alert.metric === activeAlert.metric;
                  return (
                    <tr 
                      key={`${alert.alert_code}-${alert.entity_id}-${alert.metric}-${alert.dt ?? 'control'}-${index}`}
                      onClick={() => setSelectedAlert(alert)}
                      className={isSelected ? 'selected-row' : ''}
                      style={{ cursor: 'pointer', backgroundColor: isSelected ? 'rgba(57, 208, 200, 0.15)' : undefined }}
                    >
                      <td>
                        <span className={`status-pill tone-${statusTone(alert.severity)}`}>{label('risk', alert.severity)}</span>
                      </td>
                      <td>{alert.dt ?? '对照样本'}</td>
                      <td>{alert.entity_label}</td>
                      <td>{label('entityType', alert.entity_type)}</td>
                      <td>{fieldLabel(alert.metric)}</td>
                      <td>{label('direction', alert.direction)}</td>
                      <td>{number(alert.actual)}</td>
                      <td>{number(alert.baseline)}</td>
                      <td>{percent(alert.delta_rate)}</td>
                      <td>{score(alert.robust_z)}</td>
                      <td>{algorithmCopy(alert.recommended_action)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </details>
    </>
  );
}
