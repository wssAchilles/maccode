import { AlertTriangle, AreaChart, Gauge, ShieldCheck, TrendingDown } from 'lucide-react';
import { useMemo, useState } from 'react';
import {
  useForecastingBacktest,
  useForecastingEntities,
  useForecastingQuality,
  useForecastingRisks,
  useForecastingSeries,
  useForecastingSummary,
} from '../api/hooks';
import { ChartPanel, type DashboardChartOption } from '../components/ChartPanel';
import type { ForecastingEntity, ForecastingRisk, ForecastingSeriesPoint } from '../types/api';

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : 'pending';
}

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : 'pending';
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : 'pending';
}

function score(value?: number | null) {
  return typeof value === 'number' ? value.toFixed(4) : 'pending';
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
  return metric === 'purchase_count' ? '购买量' : 'GMV';
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
        name: `${metricLabel(metric)} sparse baseline`,
        type: 'line',
        smooth: false,
        symbolSize: sparse ? 7 : 5,
        lineStyle: { width: 3, color: sparse ? '#f59e0b' : '#39d0c8', type: sparse ? 'dashed' : 'solid' },
        areaStyle: { color: sparse ? '#f59e0b22' : '#39d0c822' },
        data: values,
      },
      {
        name: 'Lower bound',
        type: 'line',
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1, color: '#64748b', type: 'dotted' },
        data: lower,
      },
      {
        name: 'Upper bound',
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
  const risks = useForecastingRisks({ severity: severity || undefined, limit: 80 });
  const quality = useForecastingQuality();
  const hasError = summary.isError || entities.isError || series.isError || backtest.isError || risks.isError || quality.isError;
  const sparse = Boolean(quality.data?.metrics.sparse_history || series.data?.some((row) => row.fallback_reason));
  const selectedRisk = useMemo(() => selectedRiskForEntity(risks.data ?? [], selectedEntity), [risks.data, selectedEntity]);
  const chartOption = useMemo(() => forecastOption(series.data ?? [], sparse, metric), [metric, series.data, sparse]);

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">Demand forecasting & revenue risk</span>
        <h1>需求预测与营收风险</h1>
        <p>用真实 Kaggle 电商行为数据生成未来 GMV 与购买量规划信号，并用质量门禁明确标记稀疏历史和低置信结果。</p>
      </section>

      {hasError ? <div className="error-banner">预测缓存尚未完整生成，请先运行 Spark 刷新任务。</div> : null}
      {sparse ? (
        <div className="error-banner">
          历史窗口不足，仅展示 sparse baseline fallback；该结果只能用于方向性复核，不应用作预算承诺或自动补货依据。
        </div>
      ) : null}

      <section className="ops-command-band">
        <div>
          <span className={`status-pill tone-${statusTone(summary.data?.quality_status)}`}>
            {summary.data?.quality_status ?? 'pending'}
          </span>
          <h2>{summary.data?.contract_version ?? 'demand-forecasting/v1'}</h2>
          <p>{summary.data?.recommended_action ?? '等待预测质量报告'}</p>
        </div>
        <AreaChart size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>未来 GMV</span>
          <strong>{money(summary.data?.site_forecast_gmv)}</strong>
          <small>{number(summary.data?.forecast_horizon_days)} day forecast horizon</small>
        </article>
        <article className="metric-card">
          <span>预测购买量</span>
          <strong>{number(summary.data?.site_forecast_purchase_count)}</strong>
          <small>{number(summary.data?.entity_count)} forecast entities</small>
        </article>
        <article className="metric-card tone-warning">
          <span>高风险实体</span>
          <strong>{number(summary.data?.high_risk_count)}</strong>
          <small>{number(summary.data?.risk_count)} risks total</small>
        </article>
        <article className="metric-card tone-danger">
          <span>历史覆盖</span>
          <strong>{number(summary.data?.history_days)} 天</strong>
          <small>{summary.data?.history_range.min_dt ?? 'pending'} → {summary.data?.history_range.max_dt ?? 'pending'}</small>
        </article>
      </section>

      <section className="toolbar forecast-toolbar" aria-label="预测筛选">
        <label>
          <span>实体</span>
          <select value={selectedEntityKey} onChange={(event) => setSelectedEntityKey(event.target.value)}>
            {(entities.data ?? []).map((entity) => (
              <option key={`${entity.scope}:${entity.entity_key}`} value={`${entity.scope}:${entity.entity_key}`}>
                {scopeLabel(entity.scope)} · {entity.entity_label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>指标</span>
          <select value={metric} onChange={(event) => setMetric(event.target.value)}>
            <option value="gmv">GMV</option>
            <option value="purchase_count">购买量</option>
          </select>
        </label>
        <label>
          <span>风险等级</span>
          <select value={severity} onChange={(event) => setSeverity(event.target.value)}>
            <option value="">全部</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
          </select>
        </label>
      </section>

      <section className="forecast-main-grid">
        <ChartPanel
          title="预测序列"
          subtitle={sparse ? '稀疏历史使用虚线 baseline，置信区间仅表示 fallback 宽度。' : '展示预测值和上下界。'}
          option={chartOption}
        />

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>质量门禁</h2>
              <p>历史覆盖、回测误差和 sparse fallback 证据。</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <div className="quality-checks">
            {(quality.data?.checks ?? []).map((check) => (
              <div className={`quality-check tone-${check.passed ? 'success' : 'danger'}`} key={check.name}>
                <span>{check.name}</span>
                <strong>{String(check.actual)} {check.operator} {String(check.expected)}</strong>
              </div>
            ))}
          </div>
          <dl>
            <dt>Site WAPE</dt>
            <dd>{score(quality.data?.metrics.site_wape ?? null)}</dd>
            <dt>Site bias</dt>
            <dd>{score(quality.data?.metrics.site_bias ?? null)}</dd>
            <dt>Backtest rows</dt>
            <dd>{number(quality.data?.metrics.backtest_rows)}</dd>
          </dl>
        </article>
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
            <dt>Entity</dt>
            <dd>{selectedRisk ? `${scopeLabel(selectedRisk.scope)} · ${selectedRisk.entity_label}` : 'none'}</dd>
            <dt>Severity</dt>
            <dd><span className={`status-pill tone-${riskTone(selectedRisk?.severity)}`}>{selectedRisk?.severity ?? 'clear'}</span></dd>
            <dt>Risk type</dt>
            <dd>{selectedRisk?.risk_type ?? 'none'}</dd>
            <dt>History days</dt>
            <dd>{number(selectedRisk?.evidence.history_days as number | undefined)}</dd>
            <dt>Action</dt>
            <dd>{selectedRisk?.recommended_action ?? '当前筛选未发现显著风险。'}</dd>
          </dl>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>回测快照</h2>
              <p>基线预测与实际 GMV 的误差证据。</p>
            </div>
            <Gauge size={20} />
          </div>
          <div className="quality-checks">
            {(backtest.data ?? []).slice(0, 5).map((row) => (
              <div className={`quality-check tone-${row.absolute_error === 0 ? 'success' : 'warning'}`} key={`${row.dt}-${row.scope}-${row.entity_key}`}>
                <span>{row.dt}</span>
                <strong>{money(row.actual)} / error {money(row.absolute_error)}</strong>
              </div>
            ))}
            {backtest.data?.length === 0 ? (
              <div className="quality-check tone-danger">
                <span>backtest</span>
                <strong>历史不足，无法生成稳定回测。</strong>
              </div>
            ) : null}
          </div>
        </article>
      </section>

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
                <th>预测 GMV</th>
                <th>近期 GMV</th>
                <th>变化</th>
                <th>历史天数</th>
                <th>模型</th>
                <th>建议动作</th>
              </tr>
            </thead>
            <tbody>
              {(entities.data ?? []).map((entity) => (
                <tr className="forecast-row" key={`${entity.scope}-${entity.entity_key}`}>
                  <td>
                    <button
                      className="forecast-entity-button"
                      type="button"
                      onClick={() => setSelectedEntityKey(`${entity.scope}:${entity.entity_key}`)}
                    >
                      {scopeLabel(entity.scope)} · {entity.entity_label}
                    </button>
                  </td>
                  <td><span className={`status-pill tone-${riskTone(entity.risk_level)}`}>{entity.risk_level}</span></td>
                  <td>{money(entity.forecast_gmv)}</td>
                  <td>{money(entity.recent_gmv)}</td>
                  <td>{percent(entity.expected_change_rate)}</td>
                  <td>{number(entity.history_days)}</td>
                  <td><span className="event-chip">{entity.model_name}</span></td>
                  <td>{entity.recommended_action}</td>
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
    </>
  );
}
