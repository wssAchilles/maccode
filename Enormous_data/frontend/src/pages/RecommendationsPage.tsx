import { BellRing, RotateCcw, ShieldCheck } from 'lucide-react';
import {
  useRecommendationAlerts,
  useRecommendationCandidates,
  useRecommendationEvaluation,
  useRecommendationItems,
  useRecommendationQuality,
  useRecommendationSummary,
} from '../api/hooks';
import { AlgorithmEvidenceBand, type AlgorithmEvidenceTone } from '../components/AlgorithmEvidenceBand';
import { ChartPanel, type DashboardChartOption } from '../components/ChartPanel';
import { OptimizationModuleStrip } from '../features/optimization/OptimizationImpactPanel';
import { algorithmCopy, displayValue, fieldLabel, label, listLabels, statusLabel } from '../i18n/displayText';
import { donutOption, horizontalBarOption } from '../lib/chartOptions';
import type { NamedValue, RecommendationCandidate, RecommendationEvaluationMetric, RecommendationItem, RecommendationTopKCell } from '../types/api';

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '待生成';
}

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : '待生成';
}

function score(value: unknown) {
  if (typeof value === 'number') return value.toFixed(4);
  if (typeof value === 'string') return displayValue(value);
  return value == null ? '待生成' : String(value);
}

function freshness(minutes?: number | null) {
  if (typeof minutes !== 'number') {
    return '待生成';
  }
  const days = minutes / 1440;
  return days >= 1 ? `${days.toFixed(1)} 天` : `${minutes.toFixed(0)} 分钟`;
}

function riskTone(value: 'success' | 'warning' | 'danger') {
  return value;
}

function statusTone(status: string) {
  if (status === 'passed') return 'success';
  if (status.includes('degraded') || status.includes('review')) return 'warning';
  return 'danger';
}

function publishTone(canPromote: boolean, status: string): AlgorithmEvidenceTone {
  if (canPromote) return 'success';
  if (status.includes('degraded') || status.includes('review') || status === 'pending') return 'warning';
  return 'danger';
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

function confidenceRows(rows: RecommendationItem[]): NamedValue[] {
  return rows
    .slice()
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 10)
    .map((row) => ({ name: shortLabel(`${displayValue(row.brand)} ${row.product_id}`), value: Number((row.confidence * 100).toFixed(1)) }));
}

function candidateScoreRows(rows: RecommendationCandidate[]): NamedValue[] {
  return rows
    .slice()
    .sort((a, b) => b.ranker_score - a.ranker_score)
    .slice(0, 10)
    .map((row) => ({ name: shortLabel(`${displayValue(row.brand)} ${row.product_id}`), value: Number((row.ranker_score * 100).toFixed(1)) }));
}

function candidateContributionRows(rows: RecommendationCandidate[]): NamedValue[] {
  if (!rows.length) return [];
  const metrics: Array<keyof Pick<RecommendationCandidate, 'ranker_score' | 'conversion_score' | 'freshness_score' | 'affinity_score' | 'source_score'>> = [
    'ranker_score',
    'conversion_score',
    'freshness_score',
    'affinity_score',
    'source_score',
  ];
  return metrics
    .map((metric) => {
      const total = rows.reduce((sum, row) => sum + (Number(row[metric]) || 0), 0);
      return { name: fieldLabel(metric), value: Number(((total / rows.length) * 100).toFixed(1)) };
    })
    .sort((a, b) => b.value - a.value);
}

function metricPercent(value: number | null | undefined) {
  return typeof value === 'number' ? Number((value * 100).toFixed(1)) : null;
}

function evaluationMetricRows(rows: RecommendationEvaluationMetric[]): NamedValue[] {
  return rows.flatMap((row) => {
    const model = label('model', row.model_name);
    return [
      { name: `${model} · 召回率`, value: metricPercent(row.recall_at_k) },
      { name: `${model} · 精确率`, value: metricPercent(row.precision_at_k) },
      { name: `${model} · 排序增益`, value: metricPercent(row.ndcg_at_k) },
      { name: `${model} · 目录覆盖`, value: metricPercent(row.catalog_coverage) },
    ]
      .filter((item): item is NamedValue & { value: number } => item.value !== null)
      .map((item) => ({ name: item.name, value: item.value }));
  });
}

function evaluationSourceRows(rows: Array<{ source: string; recommendations: number }>): NamedValue[] {
  return rows.map((row) => ({ name: label('source', row.source), value: row.recommendations })).sort((a, b) => b.value - a.value);
}

function recommendationRecallFlowOption(rows: RecommendationCandidate[]): DashboardChartOption {
  const sourceCounts = countBy(rows, (row) => row.recall_stage || row.candidate_source);
  const calibrationCounts = countBy(rows, (row) => row.calibration_bucket || 'unknown');
  const sortNode = '排序候选池';
  const snapshotNode = '推荐快照';
  const nodeNames = new Set<string>([sortNode, snapshotNode]);
  const links: Array<{ source: string; target: string; value: number; stage: string; lineStyle?: { color?: string; opacity?: number; curveness?: number } }> = [];

  sourceCounts.forEach((row) => {
    const sourceName = label('source', row.name, { fallback: displayValue(row.name) });
    nodeNames.add(sourceName);
    links.push({
      source: sourceName,
      target: sortNode,
      value: row.value,
      stage: '召回来源',
      lineStyle: { color: 'gradient', opacity: 0.52, curveness: 0.5 },
    });
  });

  calibrationCounts.forEach((row) => {
    const calibrationName = `${label('risk', row.name, { fallback: displayValue(row.name) })}校准层`;
    nodeNames.add(calibrationName);
    links.push({
      source: sortNode,
      target: calibrationName,
      value: row.value,
      stage: '排序校准',
      lineStyle: { color: 'gradient', opacity: 0.42, curveness: 0.5 },
    });
    links.push({
      source: calibrationName,
      target: snapshotNode,
      value: row.value,
      stage: '快照出口',
      lineStyle: { color: 'gradient', opacity: 0.35, curveness: 0.5 },
    });
  });

  return {
    tooltip: {
      trigger: 'item',
      formatter: (rawParams) => {
        const params = Array.isArray(rawParams) ? rawParams[0] : rawParams;
        const item = params as { data?: { source?: string; target?: string; value?: number; stage?: string }; dataType?: string } | undefined;
        if (item?.dataType === 'edge') {
          return [
            `<strong>${item.data?.stage ?? '流向'}</strong>`,
            `${item.data?.source ?? '来源'} 至 ${item.data?.target ?? '目标'}`,
            `候选数量：${number(item.data?.value)}`,
          ].join('<br/>');
        }
        return item?.data?.source ?? (params as { name?: string } | undefined)?.name ?? '推荐流向';
      },
    },
    aria: {
      enabled: true,
      description: `推荐召回来源流向图，展示 ${sourceCounts.length} 个召回来源、${calibrationCounts.length} 个校准层和 ${rows.length} 条候选记录。`,
    },
    series: [
      {
        name: '推荐召回流向',
        type: 'sankey',
        data: Array.from(nodeNames).map((name) => ({ name })),
        links,
        left: 8,
        right: 18,
        top: 26,
        bottom: 12,
        nodeGap: 14,
        nodeWidth: 14,
        layoutIterations: 32,
        draggable: false,
        emphasis: {
          focus: 'adjacency',
        },
        label: {
          color: '#dbe5ee',
          fontSize: 12,
        },
        lineStyle: {
          color: 'gradient',
          opacity: 0.42,
          curveness: 0.5,
        },
        levels: [
          { depth: 0, itemStyle: { color: '#39d0c8' } },
          { depth: 1, itemStyle: { color: '#65b8ff' } },
          { depth: 2, itemStyle: { color: '#f59e0b' } },
          { depth: 3, itemStyle: { color: '#56d27b' } },
        ],
      },
    ],
  };
}

function bestRecall(rows: RecommendationEvaluationMetric[]) {
  return rows
    .filter((row) => typeof row.recall_at_k === 'number')
    .slice()
    .sort((a, b) => (b.recall_at_k ?? 0) - (a.recall_at_k ?? 0))[0];
}

export function RecommendationsPage() {
  const summary = useRecommendationSummary();
  const items = useRecommendationItems(50);
  const candidates = useRecommendationCandidates({ limit: 80 });
  const quality = useRecommendationQuality();
  const evaluation = useRecommendationEvaluation();
  const alerts = useRecommendationAlerts();
  const hasError = summary.isError || items.isError || quality.isError || alerts.isError;
  const optionalMissing = candidates.isError;
  const status = summary.data?.quality_status ?? 'pending';
  const alertRows = alerts.data ?? [];
  const fallbackTone = riskTone((summary.data?.fallback_rate ?? 0) > 0.4 ? 'danger' : (summary.data?.fallback_rate ?? 0) > 0.2 ? 'warning' : 'success');
  const confidenceTone = riskTone((summary.data?.avg_confidence ?? 0) < 0.1 ? 'danger' : (summary.data?.avg_confidence ?? 0) < 0.3 ? 'warning' : 'success');
  const freshnessTone = riskTone((summary.data?.freshness_lag_minutes ?? 0) > 10080 ? 'danger' : (summary.data?.freshness_lag_minutes ?? 0) > 1440 ? 'warning' : 'success');
  const hasBlockingRisk = [fallbackTone, confidenceTone, freshnessTone].includes('danger') || alertRows.length > 0;
  const canPromote = status === 'passed' && !hasBlockingRisk;
  const publishStatus = canPromote ? status : 'needs review';
  const itemRows = items.data ?? [];
  const candidateRows = candidates.data ?? [];
  const sourceMix = countBy(itemRows, (row) => row.source);
  const evaluationSourceMix = evaluation.data?.source_mix?.length ? evaluationSourceRows(evaluation.data.source_mix) : sourceMix;
  const candidateSourceMix = countBy(candidateRows, (row) => row.recall_stage || row.candidate_source);
  const candidateCalibrationMix = countBy(candidateRows, (row) => row.calibration_bucket);
  const rankerModelMix = countBy(candidateRows, (row) => row.ranker_model);
  const rankerScoreTop = candidateScoreRows(candidateRows);
  const contributionRows = candidateContributionRows(candidateRows);
  const evaluationRows = evaluationMetricRows(evaluation.data?.model_metrics ?? []);
  const categoryMix = countBy(itemRows, (row) => row.category_level1);
  const confidenceTop = confidenceRows(itemRows);
  const topSource = evaluationSourceMix[0];
  const topCalibration = candidateCalibrationMix[0];
  const topRankerModel = rankerModelMix[0];
  const topRankedCandidate = rankerScoreTop[0];
  const topContribution = contributionRows[0];
  const affinityContribution = contributionRows.find((row) => row.name === fieldLabel('affinity_score'));
  const topEvaluationModel = bestRecall(evaluation.data?.model_metrics ?? []);
  const topCategory = categoryMix[0];
  const topConfidence = confidenceTop[0];
  const candidateSourceSummary = candidateSourceMix.length
    ? `候选来源：${candidateSourceMix.slice(0, 4).map((row) => `${label('source', row.name)} ${number(row.value)} 条`).join('，')}。`
    : '等待候选召回产物。';
  const recallFlowOption = recommendationRecallFlowOption(candidateRows);
  const publishToneValue = publishTone(canPromote, status);

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">准实时推荐守护</span>
        <h1>准实时推荐与监控守护</h1>
        <p>用 Spark 生成可解释推荐快照，并通过质量门禁、兜底占比和回滚状态控制前端可见结果。</p>
      </section>

      {hasError ? <div className="error-banner">推荐缓存尚未生成，请先运行 Spark 刷新任务。</div> : null}
      {optionalMissing ? <div className="error-banner">候选召回与排序产物尚未生成，已保留推荐评估视图。</div> : null}

      <OptimizationModuleStrip moduleId="recommendation-release" title="推荐优化影响" />

      <AlgorithmEvidenceBand
        title="推荐证据结论"
        status={canPromote ? '可发布' : publishToneValue === 'danger' ? '已阻断' : '需复核'}
        tone={publishToneValue}
        description={canPromote ? '离线指标、质量门禁和回滚快照均满足当前发布参考条件。' : '当前推荐快照仍存在兜底、置信度、候选产物或回滚证据风险。'}
        caveat="推荐发布仍以离线门禁为准，真实业务提升需要后续随机实验验证。"
        icon={<ShieldCheck size={22} />}
        metrics={[
          {
            label: '主召回来源',
            value: topSource ? label('source', topSource.name) : '待生成',
            detail: topSource ? `${number(topSource.value)} 条` : '等待来源统计',
          },
          {
            label: '排序器',
            value: label('model', topRankerModel?.name),
            detail: topRankedCandidate ? `最高分 ${topRankedCandidate.value.toFixed(1)}%` : '等待排序候选',
          },
          {
            label: '兜底率',
            value: percent(summary.data?.fallback_rate),
            detail: `快照 ${number(summary.data?.recommendation_count)} 条`,
          },
        ]}
      />

      <section className="content-grid visual-first-grid">
        <ChartPanel
          title="模型离线评估"
          subtitle="用召回率、精确率、排序增益和目录覆盖判断推荐基线"
          option={horizontalBarOption(evaluationRows, '评估分数 %', '#39d0c8', true)}
          isEmpty={!evaluationRows.length}
          summary={
            topEvaluationModel
              ? `${label('model', topEvaluationModel.model_name)} 当前召回率最高，为 ${percent(topEvaluationModel.recall_at_k)}。`
              : '等待推荐评估结果。'
          }
        />
        <ChartPanel
          title="推荐来源占比"
          subtitle="对照个性化、算法基线和兜底来源，避免只看商品列表"
          option={donutOption(evaluationSourceMix, '推荐来源')}
          summary={topSource ? `${label('source', topSource.name)} 是当前主来源，共 ${number(topSource.value)} 条。` : '等待推荐来源数据。'}
        />
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>前 K 命中矩阵</h2>
              <p>横向比较规则推荐与矩阵分解基线的命中位置。</p>
            </div>
          </div>
          <RecommendationTopKMatrix rows={evaluation.data?.topk_matrix ?? []} />
        </article>
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>评估门禁</h2>
              <p>确认离线指标、基线产物和兜底率是否具备发布参考价值。</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <div className="quality-checks">
            {(evaluation.data?.quality_gates ?? []).map((check) => (
              <div className={`quality-check tone-${check.passed ? 'success' : 'danger'}`} key={check.name}>
                <span>{fieldLabel(check.name)}</span>
                <strong>{score(check.actual)} {check.operator} {score(check.expected)}</strong>
              </div>
            ))}
            {evaluation.data?.quality_gates.length === 0 ? (
              <div className="quality-check tone-danger">
                <span>评估门禁</span>
                <strong>等待离线评估</strong>
              </div>
            ) : null}
          </div>
        </article>
      </section>

      <section className="content-grid visual-first-grid">
        <ChartPanel
          title="召回来源流向"
          subtitle="从召回来源进入排序候选池，再流向校准层和推荐快照。"
          chartId="recommendation-recall-flow"
          option={recallFlowOption}
          isLoading={candidates.isLoading}
          isEmpty={!candidateRows.length}
          error={candidates.error instanceof Error ? candidates.error : null}
          summary={candidateSourceSummary}
        />
        <ChartPanel
          title="排序分数分布"
          subtitle="展示进入排序阶段的高分候选，避免只看最终商品列表"
          option={horizontalBarOption(rankerScoreTop, '排序分数 %', '#65b8ff')}
          isLoading={candidates.isLoading}
          isEmpty={!rankerScoreTop.length}
          summary={
            topRankedCandidate
              ? `${topRankedCandidate.name} 当前排序分数最高，为 ${topRankedCandidate.value.toFixed(1)}%，当前排序器为 ${label('model', topRankerModel?.name)}。`
              : '等待排序分数。'
          }
        />
        <ChartPanel
          title="校准分层"
          subtitle="按置信度分层观察排序器是否过度集中"
          option={donutOption(candidateCalibrationMix, '候选数量')}
          isLoading={candidates.isLoading}
          isEmpty={!candidateCalibrationMix.length}
          summary={topCalibration ? `${label('risk', topCalibration.name)}校准层当前最多，共 ${number(topCalibration.value)} 条。` : '等待校准分层。'}
        />
        <ChartPanel
          title="排序贡献结构"
          subtitle="用转化、新鲜度、图谱亲和和来源置信解释排序结果"
          option={horizontalBarOption(contributionRows, '平均贡献 %', '#f59e0b')}
          isLoading={candidates.isLoading}
          isEmpty={!contributionRows.length}
          summary={
            topContribution
              ? `${topContribution.name} 当前平均贡献最高，为 ${topContribution.value.toFixed(1)}%，${fieldLabel('affinity_score')} 为 ${(affinityContribution?.value ?? 0).toFixed(1)}%。`
              : '等待排序贡献产物。'
          }
        />
      </section>

      <section className="content-grid visual-first-grid">
        <ChartPanel
          title="推荐品类覆盖"
          subtitle="按品类查看推荐分布，避免只读商品明细"
          option={horizontalBarOption(categoryMix.slice(0, 10), '推荐数量', '#65b8ff')}
          summary={topCategory ? `${displayValue(topCategory.name)} 当前推荐覆盖最高，共 ${number(topCategory.value)} 条。` : '等待推荐品类数据。'}
        />
        <ChartPanel
          title="高置信度推荐"
          subtitle="优先查看最可信的推荐对象"
          option={horizontalBarOption(confidenceTop, '置信度 %', '#56d27b')}
          summary={topConfidence ? `${topConfidence.name} 置信度最高，为 ${topConfidence.value.toFixed(1)}%。` : '等待推荐置信度数据。'}
        />
        <ChartPanel
          title="发布风险结构"
          subtitle="把兜底、置信度、新鲜度三类风险转成可视化判断"
          option={horizontalBarOption(
            [
              { name: '兜底占比', value: Number(((summary.data?.fallback_rate ?? 0) * 100).toFixed(1)) },
              { name: '平均置信度', value: Number(((summary.data?.avg_confidence ?? 0) * 100).toFixed(1)) },
              { name: '新鲜度天数', value: Number(((summary.data?.freshness_lag_minutes ?? 0) / 1440).toFixed(1)) },
            ],
            '风险值',
            '#f59e0b',
          )}
          summary={`兜底占比 ${percent(summary.data?.fallback_rate)}，平均置信度 ${percent(summary.data?.avg_confidence)}。`}
        />
      </section>

      <section className="recommendation-triage-grid" aria-label="推荐发布风险摘要">
        <article className={`triage-card tone-${canPromote ? statusTone(status) : 'warning'}`}>
          <span>发布状态</span>
          <strong>{statusLabel(publishStatus)}</strong>
          <small>当前推荐快照 · 质量 {statusLabel(status)}</small>
          <p>{canPromote ? '门禁通过，可以发布当前快照。' : '存在发布风险，先处理风险原因。'}</p>
        </article>
        <article className="triage-card tone-danger">
          <span>风险原因</span>
          <div className="risk-list">
            <RiskRow label="兜底占比" value={percent(summary.data?.fallback_rate)} tone={fallbackTone} />
            <RiskRow label="平均置信度" value={percent(summary.data?.avg_confidence)} tone={confidenceTone} />
            <RiskRow label="新鲜度延迟" value={freshness(summary.data?.freshness_lag_minutes)} tone={freshnessTone} />
            {alertRows.length ? alertRows.map((alert) => (
              <RiskRow
                key={alert.alert_code}
                label={fieldLabel(alert.metric)}
                value={algorithmCopy(alert.recommended_action) || fieldLabel(alert.alert_code)}
                tone={alert.severity === 'critical' ? 'danger' : 'warning'}
              />
            )) : null}
          </div>
        </article>
        <article className={`triage-card tone-${summary.data?.rollback_ready ? 'warning' : 'danger'}`}>
          <span>回滚动作</span>
          <strong>{summary.data?.rollback_ready ? '可回滚' : '无历史快照'}</strong>
          <small>发布门禁 {canPromote ? '通过' : '阻断'}</small>
          <p>{summary.data?.previous_snapshot_path ?? '缺少上一版快照时，不应自动发布失败结果。'}</p>
        </article>
        <article className="triage-card tone-success">
          <span>快照证据</span>
          <strong>{number(summary.data?.recommendation_count)}</strong>
          <small>{number(summary.data?.covered_sessions)} 个覆盖会话</small>
          <p>{summary.data?.active_snapshot_path ?? '等待当前快照'}</p>
        </article>
      </section>

      <section className="ops-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>质量门禁</h2>
              <p>控制推荐覆盖、兜底占比、新鲜度、重复和非法商品。</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <div className="quality-checks">
            {(quality.data?.checks ?? []).map((check) => (
              <div className={`quality-check tone-${check.passed ? 'success' : 'danger'}`} key={check.name}>
                <span>{fieldLabel(check.name)}</span>
                <strong>{score(check.actual)} {check.operator} {score(check.expected)}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>告警与回滚</h2>
              <p>质量失败时保留上一版当前快照。</p>
            </div>
            <BellRing size={20} />
          </div>
          <div className="quality-checks">
            {(alerts.data ?? []).map((alert) => (
              <div className={`quality-check tone-${alert.severity === 'critical' ? 'danger' : 'warning'}`} key={alert.alert_code}>
                <span>{fieldLabel(alert.metric)}</span>
                <strong>{score(alert.actual)} / {score(alert.threshold)}</strong>
              </div>
            ))}
            {alerts.data?.length === 0 ? (
              <div className="quality-check tone-success">
                <span>发布门禁</span>
                <strong>通过</strong>
              </div>
            ) : null}
          </div>
          <dl>
            <dt>当前快照</dt>
            <dd>{summary.data?.active_snapshot_path ?? '待生成'}</dd>
            <dt>上一版快照</dt>
            <dd>{summary.data?.previous_snapshot_path ?? '待生成'}</dd>
          </dl>
        </article>
      </section>

      <details className="detail-table-disclosure">
        <summary>查看推荐快照明细</summary>
        <section className="data-panel jobs-panel scroll-panel">
          <div className="panel-title">
            <div>
              <h2>推荐快照</h2>
              <p>按会话输出前 K 商品，包含原因、来源和兜底标记。</p>
            </div>
            <RotateCcw size={20} />
          </div>
          <div className="table-scroll panel-scroll" aria-label="推荐快照滚动区域">
            <table>
              <thead>
                <tr>
                  <th>会话</th>
                  <th>排序</th>
                  <th>商品</th>
                  <th>品牌</th>
                  <th>类目</th>
                  <th>评分</th>
                  <th>置信度</th>
                  <th>来源</th>
                  <th>原因</th>
                </tr>
              </thead>
              <tbody>
                {itemRows.map((row) => (
                  <tr key={`${row.user_session}-${row.rank}-${row.product_id}`}>
                    <td>{row.user_session}</td>
                    <td>{row.rank}</td>
                    <td>{row.product_id}</td>
                    <td>{row.brand}</td>
                    <td>{row.category_level1}</td>
                    <td>{score(row.score)}</td>
                    <td>{percent(row.confidence)}</td>
                    <td><span className="event-chip">{label('source', row.source, { fallback: displayValue(row.source) })}</span></td>
                    <td>{listLabels('reason', row.reason_codes)}</td>
                  </tr>
                ))}
                {items.data?.length === 0 ? (
                  <tr>
                    <td colSpan={9}>等待推荐快照</td>
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

function RiskRow({ label, tone, value }: { label: string; tone: 'success' | 'warning' | 'danger'; value: string }) {
  return (
    <div className={`risk-row tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function RecommendationTopKMatrix({ rows }: { rows: RecommendationTopKCell[] }) {
  const visibleRows = rows.slice(0, 24);
  if (!visibleRows.length) {
    return <p className="empty-copy">等待前 K 命中样本。</p>;
  }

  return (
    <div className="topk-matrix" role="img" aria-label="前 K 推荐命中矩阵">
      {visibleRows.map((row) => (
        <span
          className={`topk-cell tone-${row.hit ? 'hit' : 'miss'}`}
          key={`${row.model_name}-${row.user_session}-${row.rank}-${row.product_id}`}
          title={`${label('model', row.model_name)}，第 ${row.rank} 位，商品 ${row.product_id}`}
        >
          <strong>{label('model', row.model_name)}</strong>
          <small>第 {row.rank} 位 · {row.hit ? '命中' : '未命中'}</small>
          <em>{row.product_id}</em>
        </span>
      ))}
    </div>
  );
}
