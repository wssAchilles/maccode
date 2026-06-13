import { CalendarClock, Repeat2, ShieldCheck, UsersRound } from 'lucide-react';
import { useMemo, useState } from 'react';
import {
  useCohortQuality,
  useCohortRepurchaseIntervals,
  useCohortRetention,
  useCohortSegments,
  useCohortSummary,
  useCohortValueCurves,
} from '../api/hooks';
import { algorithmCopy, displayValue, fieldLabel, label, listLabels, statusLabel } from '../i18n/displayText';
import type { CohortRetentionCell } from '../types/api';

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : '待生成';
}

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : '待生成';
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '待生成';
}

function statusTone(status?: string) {
  if (status === 'passed' || status === 'low') return 'success';
  if (status === 'needs_review' || status === 'medium') return 'queued';
  return 'failed';
}

function metricLabel(metric: string) {
  if (metric === 'repurchase_rate') return '复购率';
  if (metric === 'revenue') return '成交额';
  return '留存率';
}

function metricValue(row: CohortRetentionCell, metric: string) {
  if (metric === 'repurchase_rate') return percent(row.repurchase_rate);
  if (metric === 'revenue') return money(row.revenue);
  return percent(row.retention_rate);
}

function qualityWarningCopy(warnings: string[], sparseCohorts: string[]) {
  if (warnings.includes('insufficient_followup_periods')) {
    return '当前 cohort 只有首购周期或后续周期不足，复购和价值曲线只能用于方向性诊断。';
  }
  if (warnings.includes('empty_repurchase_intervals')) {
    return '当前没有可用复购间隔，暂不应作为自动化触达规则依据。';
  }
  if (sparseCohorts.length) {
    return `当前存在 ${sparseCohorts.join('、')} 稀疏留存分群，结果应用于方向性诊断，避免直接作为自动化触达规则。`;
  }
  return '当前留存分群质量门禁需要复核，结果应用于方向性诊断。';
}

function matrixRows(rows: CohortRetentionCell[]) {
  const cohorts = Array.from(new Set(rows.map((row) => row.cohort))).sort();
  const periods = Array.from(new Set(rows.map((row) => row.period_index))).sort((a, b) => a - b);
  const byKey = new Map(rows.map((row) => [`${row.cohort}:${row.period_index}`, row]));
  return { cohorts, periods, byKey };
}

export function CohortsPage() {
  const [selectedCohort, setSelectedCohort] = useState('');
  const [metric, setMetric] = useState('retention_rate');
  const [category, setCategory] = useState('');
  const summary = useCohortSummary();
  const retention = useCohortRetention({ cohort: selectedCohort || undefined, metric });
  const intervals = useCohortRepurchaseIntervals();
  const valueCurves = useCohortValueCurves({ cohort: selectedCohort || undefined });
  const segments = useCohortSegments({ category: category || undefined, limit: 80 });
  const quality = useCohortQuality();
  const hasError = summary.isError || retention.isError || intervals.isError || valueCurves.isError || segments.isError || quality.isError;
  const allCohorts = useMemo(
    () => Array.from(new Set([...(retention.data ?? []).map((row) => row.cohort), ...(summary.data?.sparse_cohorts ?? [])])).sort(),
    [retention.data, summary.data?.sparse_cohorts],
  );
  const matrix = useMemo(() => matrixRows(retention.data ?? []), [retention.data]);
  const riskSegments = (segments.data ?? []).filter((row) => row.risk_level !== 'low');

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">留存复购与分群经营</span>
        <h1>留存复购与分群经营分析</h1>
        <p>按首购分群追踪留存、复购、累计成交额和类目风险段，把生命周期运营从单点转化推进到长期价值管理。</p>
      </section>

      {hasError ? <div className="error-banner">留存复购缓存尚未完整生成，请先运行 Spark 刷新任务。</div> : null}
      {quality.data?.warnings.length ? (
        <div className="error-banner">{qualityWarningCopy(quality.data.warnings, quality.data.sparse_cohorts)}</div>
      ) : null}

      <section className="ops-command-band">
        <div>
          <span className={`status-pill tone-${statusTone(summary.data?.quality_status)}`}>
            {statusLabel(summary.data?.quality_status)}
          </span>
          <h2>分群经营契约 v1</h2>
          <p>{summary.data?.recommended_action ? algorithmCopy(summary.data.recommended_action) : '等待留存与复购报告'}</p>
        </div>
        <Repeat2 size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>购买用户</span>
          <strong>{number(summary.data?.purchase_user_count)}</strong>
          <small>{number(summary.data?.user_count)} 个总用户</small>
        </article>
        <article className="metric-card">
          <span>复购用户</span>
          <strong>{number(summary.data?.repeat_purchase_user_count)}</strong>
          <small>{percent(summary.data?.repeat_purchase_rate)} 复购率</small>
        </article>
        <article className="metric-card tone-warning">
          <span>二次购买区间</span>
          <strong>{summary.data?.median_days_to_second_purchase ?? '待生成'}</strong>
          <small>购买用户均收 {money(summary.data?.avg_revenue_per_purchase_user)}</small>
        </article>
        <article className="metric-card tone-danger">
          <span>高风险分群</span>
          <strong>{number(summary.data?.high_risk_cohort_count)}</strong>
          <small>分群成交额 {money(summary.data?.cohort_revenue)}</small>
        </article>
      </section>

      <section className="toolbar forecast-toolbar" aria-label="留存分群筛选">
        <label>
          <span>留存分群</span>
          <select value={selectedCohort} onChange={(event) => setSelectedCohort(event.target.value)}>
            <option value="">全部</option>
            {allCohorts.map((cohort) => (
              <option key={cohort} value={cohort}>
                {cohort}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>矩阵指标</span>
          <select value={metric} onChange={(event) => setMetric(event.target.value)}>
            <option value="retention_rate">留存率</option>
            <option value="repurchase_rate">复购率</option>
            <option value="revenue">成交额</option>
          </select>
        </label>
        <label>
          <span>类目风险</span>
          <input
            className="text-input"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            placeholder="输入原始类目，如 electronics"
          />
        </label>
      </section>

      <section className="forecast-main-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>留存分群矩阵</h2>
              <p>行是首购分群，列是首购后第 N 个周期，单元格展示当前选择的 {metricLabel(metric)}。</p>
            </div>
            <UsersRound size={20} />
          </div>
          <div className="table-scroll">
            <table aria-label="留存分群矩阵">
              <thead>
                <tr>
                  <th>留存分群</th>
                  <th>用户数</th>
                  {matrix.periods.map((period) => (
                    <th key={period}>P{period}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.cohorts.map((cohort) => {
                  const firstCell = matrix.byKey.get(`${cohort}:0`);
                  return (
                    <tr key={cohort}>
                      <td>{cohort}</td>
                      <td>{number(firstCell?.cohort_users)}</td>
                      {matrix.periods.map((period) => {
                        const cell = matrix.byKey.get(`${cohort}:${period}`);
                        return (
                          <td key={period}>
                            <span className={`status-pill tone-${statusTone(cell?.quality_status)}`}>
                              {cell ? metricValue(cell, metric) : '待生成'}
                            </span>
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>质量门禁</h2>
              <p>校验分群数量、最小分群用户数和稀疏分群警告。</p>
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
            <dt>历史天数</dt>
            <dd>{number(quality.data?.history_days)}</dd>
            <dt>分群数</dt>
            <dd>{number(quality.data?.cohort_count)}</dd>
            <dt>稀疏分群</dt>
            <dd>{quality.data?.sparse_cohorts.join('、') || '无'}</dd>
          </dl>
        </article>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>复购间隔分布</h2>
            <p>从用户首购到二次购买的周期桶，支持选择召回窗口和复购激励节奏。</p>
          </div>
          <CalendarClock size={20} />
        </div>
        <div className="table-scroll">
          <table aria-label="复购间隔分布">
            <thead>
              <tr>
                <th>区间</th>
                <th>用户</th>
                <th>占比</th>
                  <th>平均成交额</th>
              </tr>
            </thead>
            <tbody>
              {(intervals.data ?? []).map((row) => (
                <tr key={row.bucket}>
                  <td>{row.bucket}</td>
                  <td>{number(row.users)}</td>
                  <td>{percent(row.share)}</td>
                  <td>{money(row.avg_revenue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="forecast-main-grid">
        <article className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>分群价值曲线</h2>
              <p>展示周期成交额、累计成交额和每购买用户收入。</p>
            </div>
          </div>
          <div className="table-scroll">
            <table aria-label="分群价值曲线">
              <thead>
                <tr>
                  <th>留存分群</th>
                  <th>周期</th>
                  <th>成交额</th>
                  <th>累计成交额</th>
                  <th>每购买用户收入</th>
                  <th>购买用户</th>
                </tr>
              </thead>
              <tbody>
                {(valueCurves.data ?? []).map((row) => (
                  <tr key={`${row.cohort}-${row.period_index}`}>
                    <td>{row.cohort}</td>
                    <td>P{row.period_index}</td>
                    <td>{money(row.revenue)}</td>
                    <td>{money(row.cumulative_revenue)}</td>
                    <td>{money(row.revenue_per_purchase_user)}</td>
                    <td>{number(row.purchase_users)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>类目风险队列</h2>
              <p>定位低复购或样本稀疏的分群与类目组合，输出运营动作建议。</p>
            </div>
          </div>
          <div className="table-scroll">
            <table aria-label="留存分群类目风险队列">
              <thead>
                <tr>
                  <th>分段</th>
                  <th>风险</th>
                  <th>复购率</th>
                </tr>
              </thead>
              <tbody>
                {(riskSegments.length ? riskSegments : segments.data ?? []).map((row) => (
                  <tr key={row.segment_id}>
                    <td>
                      <strong>{row.cohort}</strong>
                      <br />
                      <span>{displayValue(row.category_level1)}</span>
                      <br />
                      <small>{money(row.revenue)}</small>
                      <br />
                      <small>{row.reason_codes.length ? listLabels('reason', row.reason_codes) : algorithmCopy(row.recommended_action)}</small>
                    </td>
                    <td><span className={`status-pill tone-${statusTone(row.risk_level)}`}>{label('risk', row.risk_level)}</span></td>
                    <td>{percent(row.repeat_purchase_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </>
  );
}
