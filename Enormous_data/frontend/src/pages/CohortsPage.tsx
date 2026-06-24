import { BookOpen, CalendarClock, Layers3, Repeat2, ShieldCheck, Target, UsersRound } from 'lucide-react';
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
import type { CohortRepurchaseInterval, CohortRetentionCell, CohortSegment } from '../types/api';

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

function riskCopy(risk?: string) {
  if (risk === 'high') return '高风险';
  if (risk === 'medium') return '观察';
  if (risk === 'low') return '健康';
  return '未覆盖';
}

function intervalCopy(bucket?: string) {
  if (bucket === 'same_month') return '当月复购';
  if (bucket === 'month_1') return '次月复购';
  if (bucket === 'month_2') return '两月后复购';
  if (bucket === 'later') return '长期复购';
  if (bucket === 'never') return '未复购';
  return displayValue(bucket);
}

function cohortHealth(cell?: CohortRetentionCell) {
  if (!cell) return '未观测';
  if (cell.quality_status !== 'passed') return '样本复核';
  if (cell.repurchase_rate >= 0.25) return '复购健康';
  if (cell.retention_rate >= 0.3) return '留存观察';
  return '复购风险';
}

function topPeriodFor(cohort: string, rows: CohortRetentionCell[]) {
  return rows
    .filter((row) => row.cohort === cohort)
    .slice()
    .sort((a, b) => b.period_index - a.period_index)[0];
}

function riskLevelCounts(rows: CohortSegment[]) {
  const levels = ['high', 'medium', 'low'];
  return levels.map((risk) => {
    const matched = rows.filter((row) => row.risk_level === risk);
    return {
      risk,
      segments: matched.length,
      users: matched.reduce((sum, row) => sum + row.users, 0),
      revenue: matched.reduce((sum, row) => sum + row.revenue, 0),
    };
  });
}

function segmentAction(row?: CohortSegment) {
  if (!row) return '当前类别没有代表组合，说明预览样本未覆盖或筛选条件过窄。';
  if (row.reason_codes.length) return listLabels('reason', row.reason_codes);
  return algorithmCopy(row.recommended_action);
}

const intervalCatalog = ['same_month', 'month_1', 'month_2', 'later'];

const metricGuides = [
  {
    id: 'cohort_users',
    label: '分群用户',
    formula: '该首购 cohort 内的购买用户数',
    meaning: '用来判断这个分群样本是否足够大。人数太少时，复购率和风险判断只能当参考。',
  },
  {
    id: 'repurchase_rate',
    label: '复购率',
    formula: '复购用户数 / 购买用户数',
    meaning: '用来判断这群用户是否愿意再次购买。越高说明留存和二次转化越健康。',
  },
  {
    id: 'window_users',
    label: '窗口用户',
    formula: '落在当前二次购买时间窗口的用户数',
    meaning: '用来决定运营节奏：当月复购适合即时维护，次月及以后更适合召回。',
  },
  {
    id: 'risk_coverage',
    label: '风险覆盖',
    formula: '当前风险筛选命中的 cohort × 类目组合数',
    meaning: '用来定位问题范围。数量越多，说明需要优先下钻风险队列，而不是只看总体均值。',
  },
  {
    id: 'avg_revenue',
    label: '均收',
    formula: '该窗口成交额 / 该窗口用户数',
    meaning: '用来判断这个复购窗口的商业价值。人数多但均收低，运营动作应偏向提客单价。',
  },
];

function intervalCards(rows: CohortRepurchaseInterval[]) {
  const byBucket = new Map(rows.map((row) => [row.bucket, row]));
  const extraBuckets = rows.map((row) => row.bucket).filter((bucket) => !intervalCatalog.includes(bucket));
  return [...intervalCatalog, ...extraBuckets].map((bucket) => ({
    contract_version: byBucket.get(bucket)?.contract_version ?? 'cohort-retention/v1',
    bucket,
    users: byBucket.get(bucket)?.users ?? 0,
    share: byBucket.get(bucket)?.share ?? 0,
    avg_revenue: byBucket.get(bucket)?.avg_revenue ?? 0,
  }));
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
  const [selectedInterval, setSelectedInterval] = useState('');
  const [selectedRisk, setSelectedRisk] = useState('all');
  const [activeGuide, setActiveGuide] = useState('repurchase_rate');
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
  const intervalsData = intervals.data ?? [];
  const intervalCoverage = useMemo(() => intervalCards(intervalsData), [intervalsData]);
  const retentionData = retention.data ?? [];
  const segmentsData = segments.data ?? [];
  const riskSummaries = useMemo(() => riskLevelCounts(segmentsData), [segmentsData]);
  const selectedCohortCell = selectedCohort
    ? topPeriodFor(selectedCohort, retentionData)
    : retentionData.slice().sort((a, b) => b.cohort_users - a.cohort_users)[0];
  const selectedIntervalRow = intervalCoverage.find((row) => row.bucket === selectedInterval) ?? intervalCoverage[0];
  const selectedRiskRows = selectedRisk === 'all' ? segmentsData : segmentsData.filter((row) => row.risk_level === selectedRisk);
  const representativeSegment = selectedRiskRows[0] ?? segmentsData[0];
  const maxCohortUsers = Math.max(...matrix.cohorts.map((cohort) => matrix.byKey.get(`${cohort}:0`)?.cohort_users ?? 0), 1);
  const maxIntervalUsers = Math.max(...intervalCoverage.map((row) => row.users), 1);
  const maxRiskUsers = Math.max(...riskSummaries.map((row) => row.users), 1);
  const activeMetricGuide = metricGuides.find((item) => item.id === activeGuide) ?? metricGuides[0];
  const selectedRiskLabel = selectedRisk === 'all' ? '全部风险' : riskCopy(selectedRisk);
  const selectedCohortLabel = selectedCohort || '全部 cohort';
  const nextAction =
    selectedRisk === 'high'
      ? '先查看下方类目风险队列，定位低复购或样本稀疏的类目组合。'
      : selectedIntervalRow?.users
        ? '继续查看价值曲线，确认这个复购窗口是否贡献足够成交额。'
        : '当前窗口暂无用户，建议切换到当月或次月复购窗口查看主力人群。';

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

      <section className="cohort-spotlight" aria-label="留存复购首屏控制台">
        <div className="cohort-spotlight-head">
          <div>
            <span className="eyebrow">首屏分群工作台</span>
            <h2>先回答问题，再看证据</h2>
            <p>把普通人最容易困惑的“看谁、看什么、好不好、下一步去哪”放到首屏，卡片不再只是数字容器。</p>
          </div>
          <div className="cohort-spotlight-kpi">
            <span>全局复购率</span>
            <strong>{percent(summary.data?.repeat_purchase_rate)}</strong>
            <small>{number(summary.data?.repeat_purchase_user_count)} 个复购用户</small>
          </div>
        </div>

        <div className="cohort-question-strip" aria-label="普通读者问题导览">
          <div>
            <strong>我现在看的是谁？</strong>
            <span>{selectedCohortLabel}，来自 2019 电商行为首购分群。</span>
          </div>
          <div>
            <strong>这个数字好不好？</strong>
            <span>{cohortHealth(selectedCohortCell)}，复购率 {percent(selectedCohortCell?.repurchase_rate ?? summary.data?.repeat_purchase_rate)}。</span>
          </div>
          <div>
            <strong>为什么重要？</strong>
            <span>它决定用户是继续维护、召回，还是进入风险排查。</span>
          </div>
          <div>
            <strong>下一步点哪里？</strong>
            <span>{nextAction}</span>
          </div>
        </div>

        <div className="cohort-spotlight-grid">
          <article className="cohort-decision-column">
            <div className="cohort-column-title">
              <span>第 1 步</span>
              <h3>选用户分群</h3>
              <p>回答“这批用户是谁”。</p>
            </div>
            <div className="cohort-chip-row">
              <button type="button" className={selectedCohort === '' ? 'is-active' : ''} onClick={() => setSelectedCohort('')}>
                <span>全部 cohort</span>
                <strong>{number(matrix.cohorts.length)}</strong>
                <small>所有首购月份一起看</small>
              </button>
              {matrix.cohorts.map((cohort) => {
                const firstCell = matrix.byKey.get(`${cohort}:0`);
                const latestCell = topPeriodFor(cohort, retentionData);
                return (
                  <button
                    type="button"
                    className={selectedCohort === cohort ? 'is-active' : ''}
                    key={cohort}
                    onClick={() => setSelectedCohort(cohort)}
                  >
                    <span>{cohort}</span>
                    <strong>{number(firstCell?.cohort_users)}</strong>
                    <small>{cohortHealth(latestCell)} · {percent(latestCell?.repurchase_rate)} 复购</small>
                  </button>
                );
              })}
            </div>
          </article>

          <article className="cohort-decision-column">
            <div className="cohort-column-title">
              <span>第 2 步</span>
              <h3>选复购窗口</h3>
              <p>回答“用户多久回来买”。</p>
            </div>
            <div className="cohort-chip-row">
              {intervalCoverage.map((row) => (
                <button
                  type="button"
                  className={selectedInterval === row.bucket ? 'is-active' : ''}
                  key={row.bucket}
                  onClick={() => setSelectedInterval(row.bucket)}
                >
                  <span>{intervalCopy(row.bucket)}</span>
                  <strong>{number(row.users)}</strong>
                  <small>{percent(row.share)} · 均收 {money(row.avg_revenue)}</small>
                </button>
              ))}
            </div>
          </article>

          <article className="cohort-decision-column">
            <div className="cohort-column-title">
              <span>第 3 步</span>
              <h3>选风险等级</h3>
              <p>回答“问题集中在哪里”。</p>
            </div>
            <div className="cohort-chip-row">
              <button type="button" className={selectedRisk === 'all' ? 'is-active' : ''} onClick={() => setSelectedRisk('all')}>
                <span>全部风险组合</span>
                <strong>{number(segmentsData.length)}</strong>
                <small>完整风险队列</small>
              </button>
              {riskSummaries.map((row) => (
                <button
                  type="button"
                  className={`tone-${statusTone(row.risk)}${selectedRisk === row.risk ? ' is-active' : ''}`}
                  key={row.risk}
                  onClick={() => setSelectedRisk(row.risk)}
                >
                  <span>{riskCopy(row.risk)}</span>
                  <strong>{number(row.segments)}</strong>
                  <small>{number(row.users)} 人 · {money(row.revenue)}</small>
                </button>
              ))}
            </div>
          </article>

          <aside className="cohort-spotlight-insight">
            <div>
              <span className="eyebrow">当前联动解释</span>
              <h3>{selectedCohortLabel} · {intervalCopy(selectedIntervalRow?.bucket)} · {selectedRiskLabel}</h3>
              <p>
                {representativeSegment
                  ? `${representativeSegment.cohort} / ${displayValue(representativeSegment.category_level1)}：${segmentAction(representativeSegment)}`
                  : '当前筛选没有代表组合，可切换左侧维度继续检查。'}
              </p>
            </div>
            <dl>
              <div>
                <dt>分群用户</dt>
                <dd>{number(selectedCohortCell?.cohort_users ?? summary.data?.purchase_user_count)}</dd>
              </div>
              <div>
                <dt>窗口用户</dt>
                <dd>{number(selectedIntervalRow?.users)}</dd>
              </div>
              <div>
                <dt>风险覆盖</dt>
                <dd>{number(selectedRiskRows.length || segmentsData.length)}</dd>
              </div>
              <div>
                <dt>最大风险人群</dt>
                <dd>{number(maxRiskUsers)}</dd>
              </div>
            </dl>
            <div className="cohort-next-step">
              <strong>建议下一步</strong>
              <span>{nextAction}</span>
            </div>
          </aside>
        </div>

        <div className="cohort-glossary" aria-label="指标说明">
          <div className="cohort-glossary-head">
            <BookOpen size={18} />
            <div>
              <h3>这些卡片到底代表什么？</h3>
              <p>点击一个指标，右侧会用普通话解释来源、公式和用途。</p>
            </div>
          </div>
          <div className="cohort-glossary-tabs" role="tablist" aria-label="指标释义">
            {metricGuides.map((item) => (
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
          <div className="cohort-glossary-card">
            <span>{activeMetricGuide.label}</span>
            <strong>{activeMetricGuide.formula}</strong>
            <p>{activeMetricGuide.meaning}</p>
          </div>
        </div>
      </section>

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

      <section className="cohort-console" aria-label="留存复购分群控制台">
        <div className="cohort-console-head">
          <div>
            <span className="eyebrow">分群覆盖工作台</span>
            <h2>每类分群都可见，只下钻代表证据</h2>
            <p>按首购 cohort、二次购买区间和类目风险三个维度组织，不把全量明细堆到页面上。</p>
          </div>
          <div className="cohort-console-meta">
            <span className={`status-pill tone-${statusTone(summary.data?.quality_status)}`}>{statusLabel(summary.data?.quality_status)}</span>
            <strong>{number(summary.data?.purchase_user_count)} 购买用户</strong>
          </div>
        </div>

        <div className="cohort-workbench">
          <div className="cohort-column">
            <div className="panel-title">
              <div>
                <h2>首购分群矩阵</h2>
                <p>完整展示当前缓存中的 cohort；点击后联动矩阵、价值曲线和右侧解释。</p>
              </div>
              <UsersRound size={20} />
            </div>
            <div className="cohort-card-grid">
              <button
                type="button"
                className={`cohort-tile tone-queued${selectedCohort === '' ? ' is-active' : ''}`}
                onClick={() => setSelectedCohort('')}
              >
                <span>全部分群</span>
                <strong>{number(matrix.cohorts.length)}</strong>
                <small>查看全局留存矩阵</small>
                <i style={{ width: '100%' }} />
              </button>
              {matrix.cohorts.map((cohort) => {
                const firstCell = matrix.byKey.get(`${cohort}:0`);
                const latestCell = topPeriodFor(cohort, retentionData);
                return (
                  <button
                    type="button"
                    className={`cohort-tile tone-${statusTone(firstCell?.quality_status)}${selectedCohort === cohort ? ' is-active' : ''}`}
                    key={cohort}
                    onClick={() => setSelectedCohort(cohort)}
                  >
                    <span>{cohort}</span>
                    <strong>{number(firstCell?.cohort_users)}</strong>
                    <small>{cohortHealth(latestCell)} · P{latestCell?.period_index ?? 0} {percent(latestCell?.repurchase_rate)} 复购</small>
                    <i style={{ width: firstCell?.cohort_users ? `${Math.max(4, (firstCell.cohort_users / maxCohortUsers) * 100)}%` : '0%' }} />
                  </button>
                );
              })}
            </div>
          </div>

          <aside className="cohort-inspector" aria-label="留存复购解释器">
            <div className="panel-title">
              <div>
                <h2>{selectedCohort || '全局'} 经营解释器</h2>
                <p>把矩阵、区间和类目风险转成答辩可说明的经营动作。</p>
              </div>
              <Target size={20} />
            </div>
            <dl className="cohort-inspector-metrics">
              <div>
                <dt>分群用户</dt>
                <dd>{number(selectedCohortCell?.cohort_users ?? summary.data?.purchase_user_count)}</dd>
              </div>
              <div>
                <dt>复购率</dt>
                <dd>{percent(selectedCohortCell?.repurchase_rate ?? summary.data?.repeat_purchase_rate)}</dd>
              </div>
              <div>
                <dt>复购窗口</dt>
                <dd>{intervalCopy(selectedIntervalRow?.bucket ?? summary.data?.median_days_to_second_purchase)}</dd>
              </div>
              <div>
                <dt>风险组合</dt>
                <dd>{number(selectedRiskRows.length || segmentsData.length)}</dd>
              </div>
            </dl>
            <div className="cohort-action-note">
              <strong>当前解释</strong>
              <p>
                {representativeSegment
                  ? `${representativeSegment.cohort} / ${displayValue(representativeSegment.category_level1)}：${segmentAction(representativeSegment)}`
                  : '当前筛选没有代表风险组合，可从左侧切换 cohort 或风险级别继续检查。'}
              </p>
            </div>
          </aside>
        </div>

        <div className="cohort-signal-grid">
          <article>
            <div className="panel-title">
              <div>
                <h2>复购区间覆盖</h2>
                <p>显示所有二次购买窗口，不展开到用户明细。</p>
              </div>
              <CalendarClock size={20} />
            </div>
            <div className="cohort-mini-grid">
              {intervalCoverage.map((row) => (
                <button
                  type="button"
                  className={`cohort-mini-card${selectedInterval === row.bucket ? ' is-active' : ''}`}
                  key={row.bucket}
                  onClick={() => setSelectedInterval(row.bucket)}
                >
                  <span>{intervalCopy(row.bucket)}</span>
                  <strong>{number(row.users)}</strong>
                  <small>{percent(row.share)} · 均收 {money(row.avg_revenue)}</small>
                  <i style={{ width: row.users ? `${Math.max(4, (row.users / maxIntervalUsers) * 100)}%` : '0%' }} />
                </button>
              ))}
            </div>
          </article>

          <article>
            <div className="panel-title">
              <div>
                <h2>类目风险覆盖</h2>
                <p>按高/中/低风险展示分群覆盖，点击切换代表风险队列。</p>
              </div>
              <Layers3 size={20} />
            </div>
            <div className="cohort-risk-strip">
              <button
                type="button"
                className={selectedRisk === 'all' ? 'is-active' : ''}
                onClick={() => setSelectedRisk('all')}
              >
                <span>全部风险</span>
                <strong>{number(segmentsData.length)}</strong>
              </button>
              {riskSummaries.map((row) => (
                <button
                  type="button"
                  className={`tone-${statusTone(row.risk)}${selectedRisk === row.risk ? ' is-active' : ''}`}
                  key={row.risk}
                  onClick={() => setSelectedRisk(row.risk)}
                >
                  <span>{riskCopy(row.risk)}</span>
                  <strong>{number(row.segments)}</strong>
                  <small>{number(row.users)} 人 · {money(row.revenue)}</small>
                </button>
              ))}
            </div>
          </article>
        </div>
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
