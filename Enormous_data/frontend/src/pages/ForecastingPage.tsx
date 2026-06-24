import { AlertTriangle, AreaChart, BookOpen, Gauge, LineChart, ShieldCheck, Target, TrendingDown } from 'lucide-react';
import { useMemo, useState } from 'react';
import {
  useForecastingBacktest,
  useForecastingEntities,
  useForecastingEvaluation,
  useForecastingQuality,
  useForecastingRisks,
  useForecastingSeries,
  useForecastingSummary,
} from '../api/hooks';
import { ChartPanel, type DashboardChartOption } from '../components/ChartPanel';
import { OptimizationModuleStrip } from '../features/optimization/OptimizationImpactPanel';
import { algorithmCopy, displayValue, fieldLabel, label, statusLabel } from '../i18n/displayText';
import { donutOption, horizontalBarOption } from '../lib/chartOptions';
import type { ForecastingEntity, ForecastingEvaluationMetric, ForecastingRisk, ForecastingSeriesPoint, NamedValue } from '../types/api';

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : '待生成';
}

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : '待生成';
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '待生成';
}

function score(value?: number | null) {
  return typeof value === 'number' ? value.toFixed(4) : '待生成';
}

function statusTone(status?: string) {
  if (status === 'passed') return 'success';
  if (status === 'needs_review') return 'queued';
  if (status === 'high' || status === 'failed') return 'failed';
  return 'queued';
}

function riskTone(level?: string) {
  if (level === 'high') return 'failed';
  if (level === 'medium') return 'queued';
  return 'success';
}

function scopeLabel(scope?: string) {
  if (scope === 'site') return '全站';
  if (scope === 'category') return '类目';
  return scope ?? '实体';
}

function metricLabel(metric: string) {
  return metric === 'purchase_count' ? '购买量' : '成交额';
}

function shortLabel(value: string) {
  return value.length > 18 ? `${value.slice(0, 16)}...` : value;
}

function countBy<T>(rows: T[], keyFn: (row: T) => string): NamedValue[] {
  const counts = new Map<string, number>();
  rows.forEach((row) => {
    const key = keyFn(row) || 'unknown';
    counts.set(key, (counts.get(key) ?? 0) + 1);
  });
  return Array.from(counts.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

function topForecastGmvRows(rows: ForecastingEntity[]): NamedValue[] {
  return rows
    .slice()
    .sort((a, b) => b.forecast_gmv - a.forecast_gmv)
    .slice(0, 10)
    .map((row) => ({ name: shortLabel(`${scopeLabel(row.scope)} ${displayValue(row.entity_label)}`), value: Math.round(row.forecast_gmv) }));
}

function changeRows(rows: ForecastingEntity[]): NamedValue[] {
  return rows
    .slice()
    .sort((a, b) => Math.abs(b.expected_change_rate) - Math.abs(a.expected_change_rate))
    .slice(0, 10)
    .map((row) => ({ name: shortLabel(`${scopeLabel(row.scope)} ${displayValue(row.entity_label)}`), value: Number((row.expected_change_rate * 100).toFixed(1)) }));
}

function horizonLabel(group?: string) {
  const match = group?.match(/^h(\d+)$/);
  if (match) return `${match[1]} 日跨度`;
  return group ? label('model', group, { fallback: fieldLabel(group) }) : '整体';
}

function evaluationRows(rows: ForecastingEvaluationMetric[], metric: 'wape' | 'bias'): NamedValue[] {
  return rows
    .map((row) => {
      const name = row.group ? horizonLabel(row.group) : row.window_days ? `${row.window_days} 日窗口` : '整体';
      const value = row[metric];
      return typeof value === 'number' ? { name, value: Number((value * 100).toFixed(1)) } : null;
    })
    .filter((row): row is NamedValue => Boolean(row));
}

function checkValue(value: unknown) {
  if (typeof value === 'number') return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(4);
  if (typeof value === 'boolean') return value ? '是' : '否';
  return value == null ? '待生成' : String(value);
}

const forecastMetricGuides = [
  {
    id: 'forecast_gmv',
    label: '未来成交额',
    formula: '未来窗口内每天预测成交额求和',
    meaning: '回答未来 7 天大概会产生多少销售额，只能作为计划信号，不是确定收入承诺。',
  },
  {
    id: 'forecast_purchase_count',
    label: '预测购买量',
    formula: '未来窗口内预测购买事件数求和',
    meaning: '回答未来可能有多少次购买，用来估算运营、库存和推荐位承载压力。',
  },
  {
    id: 'history_coverage',
    label: '历史覆盖',
    formula: '可用于训练和回测的历史天数',
    meaning: '历史越短，预测越容易退化为兜底基线；这里是判断可信度的第一入口。',
  },
  {
    id: 'wape',
    label: 'WAPE',
    formula: '绝对误差总和 / 实际值总和',
    meaning: '衡量预测整体偏离实际多少，越低越好；它比单日误差更适合看总体可靠性。',
  },
  {
    id: 'bias',
    label: 'Bias',
    formula: '(实际值 - 预测值) / 实际值',
    meaning: '判断模型是系统性高估还是低估。正数偏保守，负数代表预测偏高。',
  },
  {
    id: 'risk_entity',
    label: '高风险实体',
    formula: '历史不足、误差高或变化异常的预测对象数量',
    meaning: '告诉你哪些预测不该直接拿去做预算或补货，需要先看风险证据。',
  },
];

function forecastTrustCopy(sparse: boolean, qualityStatus?: string) {
  if (sparse) return '可信度偏低：历史窗口不足，当前结果主要是稀疏基线兜底。';
  if (qualityStatus === 'passed') return '可信度可用：质量门禁通过，可作为计划参考。';
  return '需要复核：请先查看质量门禁和回测误差。';
}

function riskPlainCopy(level?: string) {
  if (level === 'high') return '高风险';
  if (level === 'medium') return '中风险';
  if (level === 'low') return '低风险';
  return '全部风险';
}

function modelPlainCopy(model?: string) {
  if (model === 'sparse_baseline_fallback') return '稀疏基线兜底';
  if (model === 'rolling_baseline_backtest') return '滚动基线回测';
  if (model === 'weekday_baseline_backtest') return '星期季节性基线';
  return model ? label('model', model, { fallback: fieldLabel(model) }) : '待生成';
}

function forecastAria(metric: string) {
  return {
    show: true,
    decal: { show: true },
    label: { description: `预测折线图，指标为${metricLabel(metric)}，展示预测值和上下界。` },
  };
}

function forecastOption(rows: ForecastingSeriesPoint[], sparse: boolean, metric: string): DashboardChartOption {
  const ordered = [...rows].sort((a, b) => a.dt.localeCompare(b.dt));
  const axis = ordered.map((row) => row.dt);
  const values = ordered.map((row) => row.forecast_value);
  const lower = ordered.map((row) => row.lower_bound);
  const upper = ordered.map((row) => row.upper_bound);
  const finiteValues = [...values, ...lower, ...upper].filter((value) => Number.isFinite(value));
  const minValue = finiteValues.length ? Math.min(...finiteValues) : 0;
  const maxValue = finiteValues.length ? Math.max(...finiteValues) : 1;
  const padding = Math.max((maxValue - minValue) * 0.12, Math.abs(maxValue) * 0.03, 1);

  return {
    textStyle: {
      fontFamily: 'Inter, "Microsoft YaHei", system-ui, sans-serif',
      color: '#d8e2ee',
    },
    aria: forecastAria(metric),
    tooltip: {
      trigger: 'axis',
    },
    legend: {
      top: 0,
      textStyle: { color: '#9fb2c8' },
    },
    grid: { top: 48, right: 24, bottom: 42, left: 72 },
    xAxis: {
      type: 'category',
      data: axis,
      axisLabel: { color: '#8fa2b7' },
      axisLine: { lineStyle: { color: '#26384c' } },
    },
    yAxis: {
      type: 'value',
      scale: true,
      min: Math.max(0, Math.floor((minValue - padding) * 100) / 100),
      max: Math.ceil((maxValue + padding) * 100) / 100,
      splitLine: { lineStyle: { color: '#203247' } },
      axisLabel: { color: '#8fa2b7' },
    },
    series: [
      {
        name: sparse ? `${metricLabel(metric)}稀疏基线` : `${metricLabel(metric)}预测值`,
        type: 'line',
        smooth: false,
        symbolSize: sparse ? 7 : 5,
        lineStyle: { width: 3, color: sparse ? '#f59e0b' : '#39d0c8', type: sparse ? 'dashed' : 'solid' },
        areaStyle: { color: sparse ? '#f59e0b22' : '#39d0c822' },
        data: values,
      },
      {
        name: '下界',
        type: 'line',
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1, color: '#64748b', type: 'dotted' },
        data: lower,
      },
      {
        name: '上界',
        type: 'line',
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1, color: '#64748b', type: 'dotted' },
        data: upper,
      },
    ],
  };
}

function selectedRiskForEntity(risks: ForecastingRisk[], entity?: ForecastingEntity) {
  if (!entity) return risks[0];
  return risks.find((risk) => risk.scope === entity.scope && risk.entity_key === entity.entity_key) ?? risks[0];
}

export function ForecastingPage() {
  const [metric, setMetric] = useState('gmv');
  const [severity, setSeverity] = useState('');
  const [selectedEntityKey, setSelectedEntityKey] = useState('site:all');
  const [activeGuide, setActiveGuide] = useState('forecast_gmv');
  const summary = useForecastingSummary();
  const entities = useForecastingEntities(80);
  const selectedEntity =
    entities.data?.find((entity) => `${entity.scope}:${entity.entity_key}` === selectedEntityKey) ?? entities.data?.[0];
  const series = useForecastingSeries({
    scope: selectedEntity?.scope ?? 'site',
    entity: selectedEntity?.entity_key ?? 'all',
    metric,
  });
  const backtest = useForecastingBacktest({
    scope: selectedEntity?.scope ?? 'site',
    entity: selectedEntity?.entity_key ?? 'all',
  });
  const evaluation = useForecastingEvaluation();
  const risks = useForecastingRisks({ severity: severity || undefined, limit: 80 });
  const quality = useForecastingQuality();
  const hasError =
    summary.isError ||
    entities.isError ||
    series.isError ||
    backtest.isError ||
    risks.isError ||
    quality.isError;
  const entityRows = entities.data ?? [];
  const sparse = Boolean(quality.data?.metrics.sparse_history || series.data?.some((row) => row.fallback_reason));
  const selectedRisk = useMemo(() => selectedRiskForEntity(risks.data ?? [], selectedEntity), [risks.data, selectedEntity]);
  const chartOption = useMemo(() => forecastOption(series.data ?? [], sparse, metric), [metric, series.data, sparse]);
  const riskMix = useMemo(() => countBy(entityRows, (row) => label('risk', row.risk_level, { fallback: displayValue(row.risk_level) })), [entityRows]);
  const forecastGmvRows = useMemo(() => topForecastGmvRows(entityRows), [entityRows]);
  const expectedChangeRows = useMemo(() => changeRows(entityRows), [entityRows]);
  const modelWapeRows = useMemo(() => evaluationRows(evaluation.data?.model_metrics ?? [], 'wape'), [evaluation.data]);
  const horizonBiasRows = useMemo(() => evaluationRows(evaluation.data?.horizon_metrics ?? [], 'bias'), [evaluation.data]);
  const windowWapeRows = useMemo(() => evaluationRows(evaluation.data?.window_metrics ?? [], 'wape'), [evaluation.data]);
  const topForecastEntity = forecastGmvRows[0];
  const topRiskLevel = riskMix[0];
  const bestBacktestModel = modelWapeRows.slice().sort((a, b) => a.value - b.value)[0];
  const activeMetricGuide = forecastMetricGuides.find((item) => item.id === activeGuide) ?? forecastMetricGuides[0];
  const selectedEntityLabel = selectedEntity ? `${scopeLabel(selectedEntity.scope)} · ${displayValue(selectedEntity.entity_label)}` : '等待预测实体';
  const selectedMetricLabel = metricLabel(metric);
  const selectedRiskLabel = severity ? riskPlainCopy(severity) : '全部风险';
  const selectedForecastValue = metric === 'purchase_count' ? number(selectedEntity?.forecast_purchase_count) : money(selectedEntity?.forecast_gmv);
  const selectedRecentValue = metric === 'purchase_count' ? '近期购买量未单独输出' : money(selectedEntity?.recent_gmv);
  const confidenceCopy = forecastTrustCopy(sparse, summary.data?.quality_status);
  const nextAction =
    sparse || selectedEntity?.fallback_reason
      ? '先看质量门禁和回测误差，确认这条预测能否进入计划。'
      : selectedRisk?.severity === 'high'
        ? '先看风险证据和风险队列，避免直接把高风险预测用于预算。'
        : '可以继续查看预测序列，确认未来每天的变化节奏。';

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">预测风险</span>
        <h1>需求预测与营收风险</h1>
        <p>用真实 Kaggle 电商行为数据生成未来成交额与购买量规划信号，并用质量门禁明确标记稀疏历史和低置信结果。</p>
      </section>

      {hasError ? <div className="error-banner">预测缓存尚未完整生成，请先运行 Spark 刷新任务。</div> : null}
      {sparse ? (
        <div className="error-banner">
          历史窗口不足，仅展示稀疏基线兜底；该结果只能用于方向性复核，不应用作预算承诺或自动补货依据。
        </div>
      ) : null}

      <section className="forecast-workbench" aria-label="需求预测首屏解释工作台">
        <div className="forecast-workbench-head">
          <div>
            <span className="eyebrow">预测读图工作台</span>
            <h2>先判断能不能信，再看预测多少钱</h2>
            <p>把普通人最容易误解的预测卡片改成“选择对象、查看结果、解释可信度、跳到证据”的工作流。</p>
          </div>
          <div className={`forecast-trust-badge tone-${statusTone(summary.data?.quality_status)}`}>
            <span>预测可信度</span>
            <strong>{sparse ? '需复核' : statusLabel(summary.data?.quality_status)}</strong>
          </div>
        </div>

        <div className="forecast-question-strip" aria-label="普通读者预测问题导览">
          <div>
            <strong>我现在预测谁？</strong>
            <span>{selectedEntityLabel}</span>
          </div>
          <div>
            <strong>预测的是哪项业务量？</strong>
            <span>{selectedMetricLabel}，未来 {number(summary.data?.forecast_horizon_days)} 天窗口。</span>
          </div>
          <div>
            <strong>这个结果能直接用吗？</strong>
            <span>{confidenceCopy}</span>
          </div>
          <div>
            <strong>下一步点哪里？</strong>
            <span>{nextAction}</span>
          </div>
        </div>

        <div className="forecast-decision-grid">
          <article className="forecast-selector-panel">
            <div className="forecast-step-title">
              <span>第 1 步</span>
              <h3>选择预测对象</h3>
              <p>先确定你看的预测是全站、类目还是具体实体。</p>
            </div>
            <div className="forecast-entity-picker">
              {(entities.data ?? []).map((entity) => {
                const key = `${entity.scope}:${entity.entity_key}`;
                return (
                  <button
                    type="button"
                    className={selectedEntityKey === key ? 'is-active' : ''}
                    key={key}
                    onClick={() => setSelectedEntityKey(key)}
                  >
                    <span>{scopeLabel(entity.scope)} · {displayValue(entity.entity_label)}</span>
                    <strong>{money(entity.forecast_gmv)}</strong>
                    <small>{riskPlainCopy(entity.risk_level)} · {modelPlainCopy(entity.model_name)}</small>
                  </button>
                );
              })}
            </div>
          </article>

          <article className="forecast-selector-panel">
            <div className="forecast-step-title">
              <span>第 2 步</span>
              <h3>选择预测指标</h3>
              <p>成交额用于预算，购买量用于运营承载。</p>
            </div>
            <div className="forecast-toggle-grid">
              <button type="button" className={metric === 'gmv' ? 'is-active' : ''} onClick={() => setMetric('gmv')}>
                <span>成交额</span>
                <strong>{money(selectedEntity?.forecast_gmv)}</strong>
                <small>未来销售规模</small>
              </button>
              <button type="button" className={metric === 'purchase_count' ? 'is-active' : ''} onClick={() => setMetric('purchase_count')}>
                <span>购买量</span>
                <strong>{number(selectedEntity?.forecast_purchase_count)}</strong>
                <small>未来购买事件</small>
              </button>
            </div>
            <div className="forecast-step-title is-secondary">
              <span>第 3 步</span>
              <h3>选择风险范围</h3>
              <p>风险筛选会联动风险队列和当前风险解释。</p>
            </div>
            <div className="forecast-risk-buttons">
              {[
                { value: '', label: '全部风险' },
                { value: 'high', label: '高风险' },
                { value: 'medium', label: '中风险' },
              ].map((item) => (
                <button
                  type="button"
                  className={severity === item.value ? 'is-active' : ''}
                  key={item.value || 'all'}
                  onClick={() => setSeverity(item.value)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </article>

          <article className="forecast-insight-panel">
            <div className="panel-title">
              <div>
                <h2>{selectedEntityLabel} 预测解释器</h2>
                <p>把预测值、历史覆盖和风险证据翻译成计划动作。</p>
              </div>
              <Target size={20} />
            </div>
            <dl className="forecast-insight-metrics">
              <div>
                <dt>当前预测</dt>
                <dd>{selectedForecastValue}</dd>
              </div>
              <div>
                <dt>近期基准</dt>
                <dd>{selectedRecentValue}</dd>
              </div>
              <div>
                <dt>历史覆盖</dt>
                <dd>{number(selectedEntity?.history_days ?? summary.data?.history_days)} 天</dd>
              </div>
              <div>
                <dt>风险范围</dt>
                <dd>{selectedRiskLabel}</dd>
              </div>
            </dl>
            <div className="forecast-action-note">
              <strong>当前解释</strong>
              <p>{confidenceCopy} {selectedRisk?.recommended_action ? algorithmCopy(selectedRisk.recommended_action) : '当前筛选未发现显著风险。'}</p>
            </div>
            <div className="forecast-evidence-links" aria-label="证据跳转说明">
              <span><LineChart size={16} /> 预测序列会更新为当前实体和指标</span>
              <span><Gauge size={16} /> 回测误差说明预测偏离历史多少</span>
              <span><AlertTriangle size={16} /> 风险队列解释为什么需复核</span>
              <span><ShieldCheck size={16} /> 质量门禁决定能否用于计划</span>
            </div>
          </article>
        </div>

        <div className="forecast-glossary" aria-label="预测指标说明">
          <div className="forecast-glossary-head">
            <BookOpen size={18} />
            <div>
              <h3>这些预测卡片到底代表什么？</h3>
              <p>点击指标名查看来源、公式和普通业务解释。</p>
            </div>
          </div>
          <div className="forecast-glossary-tabs" role="tablist" aria-label="预测指标释义">
            {forecastMetricGuides.map((item) => (
              <button
                type="button"
                role="tab"
                aria-selected={activeGuide === item.id}
                className={activeGuide === item.id ? 'is-active' : ''}
                key={item.id}
                onClick={() => setActiveGuide(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="forecast-glossary-card">
            <span>{activeMetricGuide.label}</span>
            <strong>{activeMetricGuide.formula}</strong>
            <p>{activeMetricGuide.meaning}</p>
          </div>
        </div>
      </section>

      <OptimizationModuleStrip moduleId="forecast-planning" title="预测优化影响" />

      <section className="ops-command-band">
        <div>
          <span className={`status-pill tone-${statusTone(summary.data?.quality_status)}`}>
            {statusLabel(summary.data?.quality_status)}
          </span>
          <h2>{summary.data?.contract_version ? '需求预测契约 v1' : '等待需求预测契约'}</h2>
          <p>{summary.data?.recommended_action ? algorithmCopy(summary.data.recommended_action) : '等待预测质量报告'}</p>
        </div>
        <AreaChart size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>未来成交额</span>
          <strong>{money(summary.data?.site_forecast_gmv)}</strong>
          <small>{number(summary.data?.forecast_horizon_days)} 天预测窗口</small>
        </article>
        <article className="metric-card">
          <span>预测购买量</span>
          <strong>{number(summary.data?.site_forecast_purchase_count)}</strong>
          <small>{number(summary.data?.entity_count)} 个预测实体</small>
        </article>
        <article className="metric-card tone-warning">
          <span>高风险实体</span>
          <strong>{number(summary.data?.high_risk_count)}</strong>
          <small>{number(summary.data?.risk_count)} 个风险项</small>
        </article>
        <article className="metric-card tone-danger">
          <span>历史覆盖</span>
          <strong>{number(summary.data?.history_days)} 天</strong>
          <small>{summary.data?.history_range.min_dt ?? '待生成'} → {summary.data?.history_range.max_dt ?? '待生成'}</small>
        </article>
      </section>

      <section className="toolbar forecast-toolbar" aria-label="预测筛选">
        <label>
          <span>实体</span>
          <select value={selectedEntityKey} onChange={(event) => setSelectedEntityKey(event.target.value)}>
            {(entities.data ?? []).map((entity) => (
              <option key={`${entity.scope}:${entity.entity_key}`} value={`${entity.scope}:${entity.entity_key}`}>
                {scopeLabel(entity.scope)} · {displayValue(entity.entity_label)}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>指标</span>
          <select value={metric} onChange={(event) => setMetric(event.target.value)}>
            <option value="gmv">成交额</option>
            <option value="purchase_count">购买量</option>
          </select>
        </label>
        <label>
          <span>风险等级</span>
          <select value={severity} onChange={(event) => setSeverity(event.target.value)}>
            <option value="">全部</option>
            <option value="high">高</option>
            <option value="medium">中</option>
          </select>
        </label>
      </section>

      <section className="forecast-main-grid">
        <ChartPanel
          title="预测序列"
          subtitle={sparse ? '稀疏历史使用虚线基线，置信区间仅表示兜底宽度。' : '展示预测值和上下界。'}
          option={chartOption}
        />

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>质量门禁</h2>
              <p>历史覆盖、回测误差和稀疏兜底证据。</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <div className="quality-checks">
            {(quality.data?.checks ?? []).map((check) => (
              <div className={`quality-check tone-${check.passed ? 'success' : 'danger'}`} key={check.name}>
                <span>{fieldLabel(check.name)}</span>
                <strong>{String(check.actual)} {check.operator} {String(check.expected)}</strong>
              </div>
            ))}
          </div>
          <dl>
            <dt>全站加权绝对百分比误差</dt>
            <dd>{score(quality.data?.metrics.site_wape ?? null)}</dd>
            <dt>全站系统性偏差</dt>
            <dd>{score(quality.data?.metrics.site_bias ?? null)}</dd>
            <dt>回测行数</dt>
            <dd>{number(quality.data?.metrics.backtest_rows)}</dd>
          </dl>
        </article>
      </section>

      <section className="content-grid visual-first-grid">
        <ChartPanel
          title="回测模型误差"
          subtitle="对比星期季节性基线和滚动基线的加权绝对误差"
          option={horizontalBarOption(modelWapeRows, '加权误差 %', '#39d0c8')}
          isEmpty={!modelWapeRows.length}
          summary={bestBacktestModel ? `${bestBacktestModel.name} 误差最低，为 ${bestBacktestModel.value.toFixed(1)}%。` : '等待回测评估结果。'}
        />
        <ChartPanel
          title="预测跨度偏差"
          subtitle="按未来第几天观察系统性偏高或偏低"
          option={horizontalBarOption(horizonBiasRows, '系统性偏差 %', '#f59e0b')}
          isEmpty={!horizonBiasRows.length}
          summary={horizonBiasRows[0] ? `${horizonBiasRows[0].name} 偏差为 ${horizonBiasRows[0].value.toFixed(1)}%。` : '等待跨度偏差结果。'}
        />
        <ChartPanel
          title="回测窗口误差"
          subtitle="多窗口回测避免只看单一切分"
          option={horizontalBarOption(windowWapeRows, '加权误差 %', '#65b8ff')}
          isEmpty={!windowWapeRows.length}
          summary={windowWapeRows[0] ? `${windowWapeRows[0].name} 误差为 ${windowWapeRows[0].value.toFixed(1)}%。` : '等待窗口误差结果。'}
        />
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>回测质量门禁</h2>
              <p>确认误差、季节性基线和样本量满足展示条件。</p>
            </div>
            <Gauge size={20} />
          </div>
          <div className="quality-checks">
            {(evaluation.data?.quality_gates ?? []).map((check) => (
              <div className={`quality-check tone-${check.passed ? 'success' : 'danger'}`} key={check.name}>
                <span>{fieldLabel(check.name)}</span>
                <strong>{checkValue(check.actual)} {check.operator} {checkValue(check.expected)}</strong>
              </div>
            ))}
            {evaluation.data?.quality_gates.length === 0 ? (
              <div className="quality-check tone-danger">
                <span>回测评估</span>
                <strong>等待评估产物</strong>
              </div>
            ) : null}
          </div>
        </article>
      </section>

      <section className="content-grid visual-first-grid">
        <ChartPanel
          title="实体预测成交额前 N"
          subtitle="先看未来营收集中在哪些实体"
          option={horizontalBarOption(forecastGmvRows, '预测成交额', '#65b8ff')}
          summary={topForecastEntity ? `${topForecastEntity.name} 预测成交额最高，为 ${money(topForecastEntity.value)}。` : '等待实体预测数据。'}
        />
        <ChartPanel
          title="风险等级结构"
          subtitle="用分布图替代逐行寻找高/中风险"
          option={donutOption(riskMix, '风险等级')}
          summary={topRiskLevel ? `${topRiskLevel.name} 风险实体最多，共 ${number(topRiskLevel.value)} 个。` : '等待风险等级数据。'}
        />
        <ChartPanel
          title="变化率最显著实体"
          subtitle="按绝对变化幅度排序，快速定位需要复核的实体"
          option={horizontalBarOption(expectedChangeRows, '变化率 %', '#f59e0b')}
          summary={expectedChangeRows[0] ? `${expectedChangeRows[0].name} 变化率最显著，为 ${expectedChangeRows[0].value.toFixed(1)}%。` : '等待变化率数据。'}
        />
        <ChartPanel
          title="回测误差快照"
          subtitle="将回测绝对误差转为前 N 条形图"
          option={horizontalBarOption(
            (backtest.data ?? []).slice(0, 10).map((row) => ({ name: row.dt, value: Math.round(row.absolute_error) })),
            '绝对误差',
            '#fb7185',
          )}
          summary={(backtest.data ?? [])[0] ? `${(backtest.data ?? [])[0].dt} 回测误差为 ${money((backtest.data ?? [])[0].absolute_error)}。` : '等待回测误差数据。'}
        />
      </section>

      <section className="ops-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>风险证据</h2>
              <p>当前实体的风险类型、样本天数和建议动作。</p>
            </div>
            <AlertTriangle size={20} />
          </div>
          <dl>
            <dt>实体</dt>
            <dd>{selectedRisk ? `${scopeLabel(selectedRisk.scope)} · ${displayValue(selectedRisk.entity_label)}` : '无'}</dd>
            <dt>严重程度</dt>
            <dd><span className={`status-pill tone-${riskTone(selectedRisk?.severity)}`}>{label('risk', selectedRisk?.severity ?? 'clear')}</span></dd>
            <dt>风险类型</dt>
            <dd>{selectedRisk?.risk_type ? fieldLabel(selectedRisk.risk_type) : '无'}</dd>
            <dt>历史天数</dt>
            <dd>{number(selectedRisk?.evidence.history_days as number | undefined)}</dd>
            <dt>建议动作</dt>
            <dd>{selectedRisk?.recommended_action ? algorithmCopy(selectedRisk.recommended_action) : '当前筛选未发现显著风险。'}</dd>
          </dl>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>回测快照</h2>
              <p>基线预测与实际成交额的误差证据。</p>
            </div>
            <Gauge size={20} />
          </div>
          <div className="quality-checks">
            {(backtest.data ?? []).slice(0, 5).map((row) => (
              <div className={`quality-check tone-${row.absolute_error === 0 ? 'success' : 'warning'}`} key={`${row.dt}-${row.scope}-${row.entity_key}`}>
                <span>{row.dt}</span>
                <strong>{money(row.actual)} / 误差 {money(row.absolute_error)}</strong>
              </div>
            ))}
            {backtest.data?.length === 0 ? (
              <div className="quality-check tone-danger">
                <span>回测</span>
                <strong>历史不足，无法生成稳定回测。</strong>
              </div>
            ) : null}
          </div>
        </article>
      </section>

      <details className="detail-table-disclosure">
        <summary>查看实体预测与风险明细</summary>
        <section className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>实体预测与风险队列</h2>
              <p>默认按风险分排序，点击实体可切换主图实体。</p>
            </div>
            <TrendingDown size={20} />
          </div>
          <div className="table-scroll">
            <table className="forecast-risk-table" aria-label="实体预测与风险队列">
              <thead>
                <tr>
                  <th>实体</th>
                  <th>等级</th>
                  <th>预测成交额</th>
                  <th>近期成交额</th>
                  <th>变化</th>
                  <th>历史天数</th>
                  <th>模型</th>
                  <th>建议动作</th>
                </tr>
              </thead>
              <tbody>
                {entityRows.map((entity) => (
                  <tr className="forecast-row" key={`${entity.scope}-${entity.entity_key}`}>
                    <td>
                      <button
                        className="forecast-entity-button"
                        type="button"
                        onClick={() => setSelectedEntityKey(`${entity.scope}:${entity.entity_key}`)}
                      >
                        {scopeLabel(entity.scope)} · {displayValue(entity.entity_label)}
                      </button>
                    </td>
                    <td><span className={`status-pill tone-${riskTone(entity.risk_level)}`}>{label('risk', entity.risk_level)}</span></td>
                    <td>{money(entity.forecast_gmv)}</td>
                    <td>{money(entity.recent_gmv)}</td>
                    <td>{percent(entity.expected_change_rate)}</td>
                    <td>{number(entity.history_days)}</td>
                    <td><span className="event-chip">{label('model', entity.model_name)}</span></td>
                    <td>{algorithmCopy(entity.recommended_action)}</td>
                  </tr>
                ))}
                {entities.data?.length === 0 ? (
                  <tr>
                    <td colSpan={8}>当前筛选无匹配预测实体。</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </details>
    </>
  );
}
