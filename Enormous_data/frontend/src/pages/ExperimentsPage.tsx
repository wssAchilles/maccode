import { FlaskConical, GitBranch, ShieldCheck } from 'lucide-react';
import {
  useExperimentAssignments,
  useExperimentCatalog,
  useExperimentGuardrails,
  useExperimentResults,
  useExperimentSegments,
  useExperimentSummary,
  useExperimentUplift,
} from '../api/hooks';
import { AlgorithmEvidenceBand, type AlgorithmEvidenceTone } from '../components/AlgorithmEvidenceBand';
import { ChartPanel, type DashboardChartOption } from '../components/ChartPanel';
import { algorithmCopy, displayValue, experimentLabel, fieldLabel, label, statusLabel } from '../i18n/displayText';
import { barOption, donutOption, horizontalBarOption, lineOption } from '../lib/chartOptions';
import type { DateValue, ExperimentResult, ExperimentSummary, NamedValue } from '../types/api';

function number(value: unknown) {
  if (typeof value === 'number') return value.toLocaleString();
  return value == null ? '待生成' : String(value);
}

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : '待生成';
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '待生成';
}

function score(value?: number | null) {
  return typeof value === 'number' ? value.toFixed(3) : '待生成';
}

function statusTone(status?: string) {
  if (status === 'passed' || status === 'ready' || status === 'positive_significant') return 'success';
  if (status === 'needs_review' || status === 'not_significant' || status === 'not_measurable') return 'warning';
  return 'danger';
}

function experimentEvidenceTone(status?: string, causalValid?: boolean): AlgorithmEvidenceTone {
  if (causalValid === false) return 'warning';
  return statusTone(status) as AlgorithmEvidenceTone;
}

function sampleRows(summary: ExperimentSummary | undefined): NamedValue[] {
  return [
    { name: '实验组', value: summary?.treatment_assignments ?? 0 },
    { name: '对照组', value: summary?.control_assignments ?? 0 },
  ];
}

function srmRows(results: ExperimentResult[]): NamedValue[] {
  return results.map((row) => ({ name: row.name, value: Number((row.srm_p_value * 100).toFixed(1)) }));
}

function liftRows(results: ExperimentResult[]): NamedValue[] {
  return results.map((row) => ({ name: row.name, value: Number((row.absolute_lift * 100).toFixed(2)) }));
}

function experimentForestOption(results: ExperimentResult[]): DashboardChartOption {
  const rows = results.slice().sort((a, b) => b.absolute_lift - a.absolute_lift);
  const bounds = rows.flatMap((row) => [row.ci_low ?? row.absolute_lift, row.ci_high ?? row.absolute_lift, row.absolute_lift, 0]);
  const minValue = Math.min(-0.02, ...bounds);
  const maxValue = Math.max(0.02, ...bounds);
  const padding = Math.max(0.01, (maxValue - minValue) * 0.16);
  const data = rows.map((row, index) => [
    index,
    row.ci_low ?? row.absolute_lift,
    row.ci_high ?? row.absolute_lift,
    row.absolute_lift,
    row.decision,
    row.name,
  ]);

  return {
    grid: { top: 24, right: 26, bottom: 36, left: 128, containLabel: true },
    tooltip: {
      trigger: 'item',
      formatter: (rawParams) => {
        const params = Array.isArray(rawParams) ? rawParams[0] : rawParams;
        const item = params as { data?: unknown; seriesName?: string } | undefined;
        const values = Array.isArray(item?.data) ? item.data : [];
        const rowIndex = item?.seriesName === '效果点' ? Number(values[1]) : Number(values[0]);
        const row = rows[rowIndex];
        if (!row) return '实验效果';
        return [
          `<strong>${row.name}</strong>`,
          `提升：${percent(row.absolute_lift)}`,
          `置信区间：${percent(row.ci_low)} 至 ${percent(row.ci_high)}`,
          `决策：${statusLabel(row.decision)}`,
          `样本比例显著性：${score(row.srm_p_value)}`,
        ].join('<br/>');
      },
    },
    aria: {
      enabled: true,
      description: `实验效果森林图，展示 ${rows.length} 个实验的效果点估计、95% 置信区间和无提升基线。`,
    },
    xAxis: {
      type: 'value',
      min: minValue - padding,
      max: maxValue + padding,
      axisLabel: {
        formatter: (value: number) => `${(value * 100).toFixed(1)}%`,
        color: '#9ca3af',
      },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } },
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.38)' } },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: rows.map((row) => row.name),
      axisLabel: {
        color: '#dbe5ee',
        width: 110,
        overflow: 'truncate',
      },
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.38)' } },
      axisTick: { show: false },
    },
    series: [
      {
        name: '置信区间',
        type: 'custom',
        data,
        encode: { x: [1, 2], y: 0, tooltip: [1, 2, 3] },
        renderItem: (_params: any, api: any) => {
          const yIndex = Number(api.value(0));
          const low = Number(api.value(1));
          const high = Number(api.value(2));
          const start = api.coord([low, yIndex]);
          const end = api.coord([high, yIndex]);
          const halfHeight = Math.max(5, api.size([0, 1])[1] * 0.16);
          const style = { stroke: '#65b8ff', lineWidth: 3, fill: undefined };
          return {
            type: 'group',
            children: [
              { type: 'line', shape: { x1: start[0], y1: start[1], x2: end[0], y2: end[1] }, style },
              { type: 'line', shape: { x1: start[0], y1: start[1] - halfHeight, x2: start[0], y2: start[1] + halfHeight }, style },
              { type: 'line', shape: { x1: end[0], y1: end[1] - halfHeight, x2: end[0], y2: end[1] + halfHeight }, style },
            ],
          };
        },
        z: 2,
      },
      {
        name: '效果点',
        type: 'scatter',
        data: rows.map((row, index) => [row.absolute_lift, index, row.ci_low, row.ci_high, row.decision, row.name]),
        symbolSize: 12,
        itemStyle: { color: '#f59e0b', borderColor: '#fff7ed', borderWidth: 1 },
        markLine: {
          symbol: 'none',
          label: { formatter: '无提升基线', color: '#9ca3af' },
          lineStyle: { color: 'rgba(248, 113, 113, 0.68)', type: 'dashed' },
          data: [{ xAxis: 0 }],
        },
        z: 4,
      },
    ],
  };
}

function upliftLineRows(rows: Array<{ decile: number; cumulative_gain: number }>): DateValue[] {
  return rows.map((row) => ({ date: `第${row.decile}档`, value: Number(row.cumulative_gain.toFixed(3)) }));
}

function topResult(results: ExperimentResult[]) {
  return results.slice().sort((a, b) => b.absolute_lift - a.absolute_lift)[0];
}

function segmentLabel(value: unknown) {
  return label('segment', value, { fallback: displayValue(value) });
}

function riskLabel(value: unknown) {
  return label('risk', value, { fallback: displayValue(value) });
}

export function ExperimentsPage() {
  const summary = useExperimentSummary();
  const catalog = useExperimentCatalog();
  const assignments = useExperimentAssignments(80);
  const segments = useExperimentSegments();
  const guardrails = useExperimentGuardrails();
  const results = useExperimentResults();
  const uplift = useExperimentUplift();
  const hasError = summary.isError || catalog.isError || assignments.isError || segments.isError || guardrails.isError;
  const optionalMissing = results.isError || uplift.isError;
  const guardrailStatus = summary.data?.guardrail_status ?? 'pending';
  const resultRows = results.data ?? [];
  const upliftRows = uplift.data?.deciles ?? [];
  const best = topResult(resultRows);
  const topUplift = uplift.data?.summary?.[0];
  const causalValid = uplift.data?.causal_valid;
  const experimentTone = experimentEvidenceTone(guardrailStatus, causalValid);

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">增长实验门禁</span>
        <h1>策略实验与效果评估</h1>
        <p>把生命周期、推荐和优化策略转成可审计的分流、SRM 样本比例检查、效果区间和增量提升框架。</p>
      </section>

      {hasError ? <div className="error-banner">实验评估缓存尚未生成，请先运行 Spark 刷新任务。</div> : null}
      {optionalMissing ? <div className="error-banner">实验结果或增量提升产物尚未生成，已保留实验设计视图。</div> : null}

      <AlgorithmEvidenceBand
        title="实验评估结论"
        status={causalValid === false ? '离线回放' : statusLabel(guardrailStatus)}
        tone={experimentTone}
        description={algorithmCopy(summary.data?.causal_caveat ?? uplift.data?.causal_caveat ?? '离线规划先验')}
        caveat={causalValid === false ? '当前没有真实随机曝光和结果回流，不宣称真实因果提升。' : '真实上线仍需持续监控 SRM、护栏和主指标。'}
        icon={<FlaskConical size={22} />}
        metrics={[
          {
            label: '样本健康',
            value: statusLabel(guardrailStatus),
            detail: `${number(summary.data?.assigned_users)} 个分流用户`,
          },
          {
            label: '最佳实验',
            value: best ? best.name : '待生成',
            detail: best ? `提升 ${percent(best.absolute_lift)}` : '等待效果区间',
          },
          {
            label: '因果状态',
            value: causalValid === false ? '不可声明' : causalValid === true ? '可评估' : '待生成',
            detail: topUplift ? `Qini ${score(topUplift.qini_auc)}` : '等待 uplift 框架',
          },
        ]}
      />

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>实验数</span>
          <strong>{number(summary.data?.experiment_count)}</strong>
          <small>{number(summary.data?.assigned_users)} 个已分流用户</small>
        </article>
        <article className="metric-card">
          <span>分流比例</span>
          <strong>{percent(summary.data?.treatment_split)}</strong>
          <small>{number(summary.data?.treatment_assignments)} 实验组 / {number(summary.data?.control_assignments)} 对照组</small>
        </article>
        <article className="metric-card tone-warning">
          <span>预期增量成交额</span>
          <strong>{money(summary.data?.expected_incremental_gmv)}</strong>
          <small>{number(summary.data?.expected_incremental_purchases)} 个预期购买增量</small>
        </article>
        <article className="metric-card">
          <span>推荐兜底</span>
          <strong>{percent(summary.data?.recommendation_coverage.covered_sessions ? summary.data.recommendation_coverage.fallback_rate : null)}</strong>
          <small>{number(summary.data?.recommendation_coverage.recommendations)} 条推荐</small>
        </article>
      </section>

      <section className="content-grid visual-first-grid">
        <ChartPanel
          title="分流样本结构"
          subtitle="实验组与对照组样本量必须先接近预期比例"
          option={donutOption(sampleRows(summary.data), '用户数')}
          isLoading={summary.isLoading}
          isEmpty={!summary.data}
          summary={`实验组占比 ${percent(summary.data?.treatment_split)}，当前已分流 ${number(summary.data?.assigned_users)} 个用户。`}
        />
        <ChartPanel
          title="样本比例失衡门禁"
          subtitle="样本比例检查通过后才解读效果区间"
          option={horizontalBarOption(srmRows(resultRows), '样本比例显著性', '#39d0c8')}
          isLoading={results.isLoading}
          isEmpty={!resultRows.length}
          summary={resultRows.length ? `最低样本比例显著性为 ${score(Math.min(...resultRows.map((row) => row.srm_p_value)))}。` : '等待实验结果产物。'}
        />
        <ChartPanel
          title="效果提升幅度"
          subtitle="按主指标展示实验组相对对照组的绝对提升"
          option={barOption(liftRows(resultRows), '提升百分点', '#65b8ff')}
          isLoading={results.isLoading}
          isEmpty={!resultRows.length}
          summary={best ? `${best.name} 当前提升最高，为 ${percent(best.absolute_lift)}，决策为 ${statusLabel(best.decision)}。` : '等待效果统计。'}
        />
      </section>

      <section className="content-grid visual-first-grid">
        <ChartPanel
          title="效果森林图"
          subtitle="线段为 95% 置信区间，圆点为实验组相对对照组的提升。"
          chartId="experiment-effect-forest"
          option={experimentForestOption(resultRows)}
          isLoading={results.isLoading}
          isEmpty={!resultRows.length}
          summary={best ? `${best.name} 当前提升 ${percent(best.absolute_lift)}，置信区间 ${percent(best.ci_low)} 至 ${percent(best.ci_high)}。` : '等待实验结果产物。'}
        />

        <ChartPanel
          title="增量提升分位"
          subtitle="按预测增量分位展示实验组与对照组差异"
          option={barOption(
            upliftRows.map((row) => ({ name: `第${row.decile}档`, value: Number((row.uplift * 100).toFixed(2)) })),
            '提升百分点',
            '#f59e0b',
          )}
          isLoading={uplift.isLoading}
          isEmpty={!upliftRows.length}
          summary={algorithmCopy(uplift.data?.causal_caveat ?? '真实增量提升需要随机曝光、对照组和结果回流后才能判断。')}
        />
        <ChartPanel
          title="累计增益曲线"
          subtitle="仅作为离线回放框架，不宣称真实因果提升"
          option={lineOption(upliftLineRows(upliftRows), '累计增益', '#56d27b', false)}
          isLoading={uplift.isLoading}
          isEmpty={!upliftRows.length}
          summary={topUplift ? `${experimentLabel(topUplift.experiment_key)} 的增益曲线面积为 ${score(topUplift.qini_auc)}。` : '等待增量提升曲线。'}
        />
      </section>

      <section className="ops-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>实验目录</h2>
              <p>先定义目标人群、主指标、观测窗口和护栏，再启动实验。</p>
            </div>
            <GitBranch size={20} />
          </div>
          <div className="quality-checks">
            {(catalog.data ?? []).map((item) => (
              <div className={`quality-check tone-${statusTone(item.status)}`} key={item.experiment_key}>
                <span>{item.name}</span>
                <strong>{fieldLabel(item.primary_metric)} · {percent(item.expected_uplift_rate)}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>实验护栏</h2>
              <p>{algorithmCopy(guardrails.data?.recommended_action ?? '等待护栏报告')}</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <div className="quality-checks">
            {(guardrails.data?.checks ?? []).map((check) => (
              <div className={`quality-check tone-${check.passed ? 'success' : 'danger'}`} key={check.name}>
                <span>{fieldLabel(check.name)}</span>
                <strong>{number(check.actual)} {check.operator} {number(check.expected)}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>

      <details className="detail-table-disclosure">
        <summary>查看分层均衡和实验结果明细</summary>
        <section className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>分层均衡</h2>
              <p>按实验、生命周期分层和实验分组检查样本分布。</p>
            </div>
          </div>
          <div className="table-scroll">
            <table aria-label="实验分层均衡">
              <thead>
                <tr>
                  <th>实验</th>
                  <th>分层</th>
                  <th>实验分组</th>
                  <th>用户数</th>
                  <th>分层占比</th>
                  <th>观测收入</th>
                  <th>预期增量成交额</th>
                </tr>
              </thead>
              <tbody>
                {(segments.data ?? []).map((row) => (
                  <tr key={`${row.experiment_key}-${row.lifecycle_segment}-${row.variant}`}>
                    <td>{experimentLabel(row.experiment_key)}</td>
                    <td>{segmentLabel(row.lifecycle_segment)}</td>
                    <td><span className={`status-pill tone-${row.variant === 'treatment' ? 'success' : 'queued'}`}>{label('variant', row.variant)}</span></td>
                    <td>{number(row.users)}</td>
                    <td>{percent(row.segment_share)}</td>
                    <td>{money(row.observed_revenue)}</td>
                    <td>{money(row.expected_incremental_gmv)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </details>

      <details className="detail-table-disclosure">
        <summary>查看分流样本</summary>
        <section className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>分流样本</h2>
              <p>稳定哈希分桶生成实验组和对照组，生产环境应保持对照组不可变。</p>
            </div>
          </div>
          <div className="table-scroll">
            <table aria-label="实验分流样本">
              <thead>
                <tr>
                  <th>用户</th>
                  <th>实验</th>
                  <th>实验分组</th>
                  <th>分桶</th>
                  <th>生命周期</th>
                  <th>风险</th>
                  <th>类目</th>
                  <th>预期购买增量</th>
                  <th>预期成交额</th>
                </tr>
              </thead>
              <tbody>
                {(assignments.data ?? []).map((row) => (
                  <tr key={`${row.experiment_key}-${row.user_id}`}>
                    <td>{row.user_id}</td>
                    <td>{experimentLabel(row.experiment_key)}</td>
                    <td><span className={`status-pill tone-${row.variant === 'treatment' ? 'success' : 'queued'}`}>{label('variant', row.variant)}</span></td>
                    <td>{row.assignment_bucket.toFixed(4)}</td>
                    <td>{segmentLabel(row.lifecycle_segment)}</td>
                    <td>{riskLabel(row.risk_band)}</td>
                    <td>{displayValue(row.preferred_category_level1)}</td>
                    <td>{percent(row.expected_incremental_purchase_prob)}</td>
                    <td>{money(row.expected_incremental_gmv)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </details>
    </>
  );
}
