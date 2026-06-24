import { BellRing, CheckCircle2, Database, GitBranch, ListChecks, RotateCcw, ShieldAlert, ShieldCheck, Sparkles } from 'lucide-react';
import { useMemo, useRef, useState } from 'react';
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
import { algorithmCopy, displayValue, fieldLabel, label, listLabels, statusLabel } from '../i18n/displayText';
import { donutOption, horizontalBarOption } from '../lib/chartOptions';
import type { NamedValue, QualityCheck, RecommendationAlert, RecommendationCandidate, RecommendationEvaluationMetric, RecommendationItem, RecommendationTopKCell } from '../types/api';

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

function sourceKey(value?: string | null) {
  return value || 'unknown';
}

function gateExpected(checks: QualityCheck[], name: string) {
  return checks.find((check) => check.name === name)?.expected;
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

function recommendationScoreRows(rows: RecommendationItem[]): NamedValue[] {
  return rows
    .slice()
    .sort((a, b) => b.score - a.score)
    .slice(0, 10)
    .map((row) => ({ name: shortLabel(`${displayValue(row.brand)} ${row.product_id}`), value: Number((row.score * 100).toFixed(2)) }));
}

function candidateScoreRows(rows: RecommendationCandidate[]): NamedValue[] {
  return rows
    .slice()
    .sort((a, b) => b.ranker_score - a.ranker_score)
    .slice(0, 10)
    .map((row) => ({ name: shortLabel(`${displayValue(row.brand)} ${row.product_id}`), value: Number((row.ranker_score * 100).toFixed(2)) }));
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

function uniqueNumberCount(values: Array<number | null | undefined>) {
  return new Set(values.filter((value): value is number => typeof value === 'number').map((value) => value.toFixed(6))).size;
}

function rangedHorizontalBarOption(rows: NamedValue[], name: string, color: string): DashboardChartOption {
  const option = horizontalBarOption(rows, name, color);
  const values = rows.map((row) => row.value).filter(Number.isFinite);
  if (!values.length) return option;
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) return option;
  const padding = Math.max((max - min) * 0.08, 0.1);
  return {
    ...option,
    xAxis: {
      ...(Array.isArray(option.xAxis) ? option.xAxis[0] : option.xAxis),
      min: Math.max(0, Number((min - padding).toFixed(2))),
      max: Number((max + padding).toFixed(2)),
      scale: true,
    },
  };
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

type RecommendationInspectorTone = 'success' | 'warning' | 'danger';

type RecommendationInspector = {
  eyebrow: string;
  title: string;
  description: string;
  tone: RecommendationInspectorTone;
  metrics: Array<{ label: string; value: string }>;
  actions: string[];
};

type RecommendationRiskRow = {
  key: string;
  label: string;
  quantity: string;
  observed: string;
  threshold: string;
  decision: string;
  tone: RecommendationInspectorTone;
  pressure: number;
};

function findCheck(checks: QualityCheck[], name: string) {
  return checks.find((check) => check.name === name);
}

function formatRecommendationMetric(name: string, value: unknown) {
  if (typeof value !== 'number') return score(value);
  if (name.includes('rate') || name.includes('confidence')) return percent(value);
  if (name.includes('freshness')) return freshness(value);
  return score(value);
}

function riskPressure(check: QualityCheck | undefined, actual: number | null | undefined) {
  if (!check || typeof actual !== 'number' || typeof check.expected !== 'number') return 0;
  if (check.expected === 0) return actual === 0 ? 0 : 100;
  if (check.operator.includes('<=')) return Math.min(100, Math.max(0, (actual / check.expected) * 100));
  if (check.operator.includes('>=')) return Math.min(100, Math.max(0, (check.expected / Math.max(actual, 0.000001)) * 100));
  return 0;
}

function buildRecommendationRiskRows({
  summary,
  quality,
  checks,
}: {
  summary?: { fallback_rate?: number; avg_confidence?: number; freshness_lag_minutes?: number } | null;
  quality?: {
    fallback_rate?: number;
    avg_confidence?: number;
    freshness_lag_minutes?: number;
    duplicate_recommendation_rate?: number;
    invalid_product_rate?: number;
  } | null;
  checks: QualityCheck[];
}): RecommendationRiskRow[] {
  const specs = [
    {
      key: 'fallback_rate',
      label: '兜底占比',
      quantity: '无法个性化推荐而使用兜底策略的比例',
      actual: quality?.fallback_rate ?? summary?.fallback_rate,
    },
    {
      key: 'avg_confidence',
      label: '平均置信度',
      quantity: '推荐排序结果的平均可信程度',
      actual: quality?.avg_confidence ?? summary?.avg_confidence,
    },
    {
      key: 'freshness_lag_minutes',
      label: '新鲜度延迟',
      quantity: '推荐快照距离最新训练/刷新产物的时间差',
      actual: quality?.freshness_lag_minutes ?? summary?.freshness_lag_minutes,
    },
    {
      key: 'duplicate_recommendation_rate',
      label: '重复推荐比例',
      quantity: '同一会话或快照中重复商品推荐的比例',
      actual: quality?.duplicate_recommendation_rate,
    },
    {
      key: 'invalid_product_rate',
      label: '非法商品比例',
      quantity: '推荐结果中无法在候选商品池验证的比例',
      actual: quality?.invalid_product_rate,
    },
  ];

  return specs.map((spec) => {
    const check = findCheck(checks, spec.key);
    const passed = check?.passed ?? true;
    return {
      key: spec.key,
      label: spec.label,
      quantity: spec.quantity,
      observed: formatRecommendationMetric(spec.key, spec.actual),
      threshold: check ? `${check.operator} ${formatRecommendationMetric(spec.key, check.expected)}` : '仅展示',
      decision: passed ? '通过' : '阻断',
      tone: passed ? 'success' : 'danger',
      pressure: Number(riskPressure(check, spec.actual).toFixed(1)),
    };
  });
}

function buildRecommendationInspector({
  selectedInspector,
  canPromote,
  status,
  fallbackRate,
  avgConfidence,
  sourceMix,
  qualityChecks,
  alerts,
  selectedSource,
}: {
  selectedInspector: string;
  canPromote: boolean;
  status: string;
  fallbackRate?: number | null;
  avgConfidence?: number | null;
  sourceMix: NamedValue[];
  qualityChecks: QualityCheck[];
  alerts: RecommendationAlert[];
  selectedSource: string;
}): RecommendationInspector {
  const selectedGate = qualityChecks.find((check) => check.name === selectedInspector);
  if (selectedGate) {
    return {
      eyebrow: '质量门禁',
      title: fieldLabel(selectedGate.name),
      description: selectedGate.passed
        ? '该门禁已通过，当前推荐快照满足这项发布约束。'
        : '该门禁未通过，发布前需要回到 Spark 产物或推荐配置排查原因。',
      tone: selectedGate.passed ? 'success' : 'danger',
      metrics: [
        { label: '实际值', value: score(selectedGate.actual) },
        { label: '判断条件', value: selectedGate.operator },
        { label: '阈值', value: score(selectedGate.expected) },
      ],
      actions: selectedGate.passed ? ['保留当前门禁', '查看快照明细'] : ['定位失败指标', '切换上一版快照'],
    };
  }

  if (selectedInspector === 'fallback') {
    const expected = gateExpected(qualityChecks, 'fallback_rate');
    return {
      eyebrow: '发布风险',
      title: '兜底率检查',
      description: '兜底率越高，说明模型无法给出个性化结果的比例越高，需要关注召回覆盖和候选质量。',
      tone: (fallbackRate ?? 0) > 0.4 ? 'danger' : (fallbackRate ?? 0) > 0.2 ? 'warning' : 'success',
      metrics: [
        { label: '当前兜底率', value: percent(fallbackRate) },
        { label: '门禁阈值', value: typeof expected === 'number' ? percent(expected) : score(expected) },
        { label: '告警数量', value: number(alerts.length) },
      ],
      actions: ['查看兜底来源', '检查候选召回'],
    };
  }

  if (selectedInspector === 'confidence') {
    const expected = gateExpected(qualityChecks, 'avg_confidence');
    return {
      eyebrow: '排序可信度',
      title: '平均置信度检查',
      description: '置信度来自推荐排序结果，低置信度会提示需要降级发布或增加人工复核。',
      tone: (avgConfidence ?? 0) < 0.1 ? 'danger' : (avgConfidence ?? 0) < 0.3 ? 'warning' : 'success',
      metrics: [
        { label: '当前置信度', value: percent(avgConfidence) },
        { label: '最低门禁', value: typeof expected === 'number' ? percent(expected) : score(expected) },
        { label: '发布状态', value: statusLabel(status) },
      ],
      actions: ['查看高置信推荐', '复核低置信来源'],
    };
  }

  if (selectedInspector === 'recall') {
    const selected = sourceMix.find((row) => row.name === selectedSource);
    return {
      eyebrow: '候选召回',
      title: '召回来源检查',
      description: selectedSource === 'all' ? '当前查看全部推荐来源，适合判断整体快照覆盖。' : '当前已按推荐来源筛选快照表，适合定位某一类来源的推荐表现。',
      tone: sourceMix.length ? 'success' : 'warning',
      metrics: [
        { label: '来源数量', value: number(sourceMix.length) },
        { label: '当前筛选', value: selectedSource === 'all' ? '全部来源' : label('source', selectedSource, { fallback: displayValue(selectedSource) }) },
        { label: '筛选条数', value: selected ? number(selected.value) : selectedSource === 'all' ? number(sourceMix.reduce((sum, row) => sum + row.value, 0)) : '0' },
      ],
      actions: ['切换来源筛选', '查看召回流向'],
    };
  }

  if (selectedInspector === 'ranking') {
    return {
      eyebrow: '排序校准',
      title: '排序器与校准检查',
      description: '排序阶段把召回候选按转化、新鲜度、亲和度和来源置信重排，决定最终快照的展示顺序。',
      tone: 'success',
      metrics: [
        { label: '排序产物', value: '候选分数 + 校准层' },
        { label: '核心证据', value: '排序分数分布' },
        { label: '解释维度', value: '5 类贡献' },
      ],
      actions: ['查看排序贡献', '查看校准分层'],
    };
  }

  if (selectedInspector === 'features') {
    return {
      eyebrow: 'Spark 产物',
      title: '特征构建检查',
      description: '后端 Spark 从行为数据生成会话、商品、来源和原因码特征，前端只消费这些缓存产物。',
      tone: 'success',
      metrics: [
        { label: '数据来源', value: 'Spark cache JSON' },
        { label: '接口层', value: 'Flask envelope' },
        { label: '前端刷新', value: 'React Query' },
      ],
      actions: ['查看特征窗口', '查看运行批次'],
    };
  }

  if (selectedInspector === 'publish') {
    return {
      eyebrow: '发布决策',
      title: canPromote ? '当前快照可发布' : '当前快照需复核',
      description: canPromote ? '质量门禁和告警均允许展示当前推荐快照。' : '存在未通过门禁或告警时，页面保留回滚证据并提示人工复核。',
      tone: canPromote ? 'success' : alerts.length ? 'danger' : 'warning',
      metrics: [
        { label: '质量状态', value: statusLabel(status) },
        { label: '告警数量', value: number(alerts.length) },
        { label: '发布判断', value: canPromote ? '可发布' : '需复核' },
      ],
      actions: canPromote ? ['发布当前快照', '保留回滚快照'] : ['查看失败门禁', '准备回滚'],
    };
  }

  return {
    eyebrow: '质量总览',
    title: '推荐守护检查器',
    description: '点击左侧 KPI、流水线节点、质量门禁或来源筛选，可以在这里查看对应解释。',
    tone: canPromote ? 'success' : alerts.length ? 'danger' : 'warning',
    metrics: [
      { label: '通过门禁', value: `${qualityChecks.filter((check) => check.passed).length}/${qualityChecks.length || '待生成'}` },
      { label: '告警数量', value: number(alerts.length) },
      { label: '发布状态', value: statusLabel(status) },
    ],
    actions: ['查看质量门禁', '查看快照明细'],
  };
}

export function RecommendationsPage() {
  const [selectedSource, setSelectedSource] = useState('all');
  const [selectedInspector, setSelectedInspector] = useState('publish');
  const [selectedDefenseView, setSelectedDefenseView] = useState<'explain' | 'gates' | 'risk'>('explain');
  const [inspectorNotice, setInspectorNotice] = useState('点击按钮会切换解释、筛选快照或滚动到对应证据。');
  const snapshotDetailsRef = useRef<HTMLDetailsElement | null>(null);
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
  // 阻断判定以后端质量门禁结果为准，前端 tone 仅用于视觉提示
  const qualityChecksFailed = (quality.data?.checks ?? []).some((check) => !check.passed);
  const hasBlockingRisk = qualityChecksFailed || alertRows.length > 0;
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
  const recommendationScoreTop = recommendationScoreRows(itemRows);
  const itemConfidenceUniqueCount = uniqueNumberCount(itemRows.map((row) => row.confidence));
  const candidateRankerUniqueCount = uniqueNumberCount(candidateRows.map((row) => row.ranker_score));
  const candidateCalibrationUniqueCount = new Set(candidateRows.map((row) => row.calibration_bucket || 'unknown')).size;
  const confidenceChartRows = itemConfidenceUniqueCount > 1 ? confidenceTop : recommendationScoreTop;
  const confidenceChartTitle = itemConfidenceUniqueCount > 1 ? '高置信度推荐' : '推荐得分分布';
  const confidenceChartSubtitle = itemConfidenceUniqueCount > 1
    ? '优先查看最可信的推荐对象'
    : '当前推荐置信度是统一门禁值，改用最终推荐得分展示商品差异';
  const confidenceChartMetric = itemConfidenceUniqueCount > 1 ? '置信度 %' : '推荐得分 %';
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
  const filteredItemRows = useMemo(
    () => itemRows.filter((row) => selectedSource === 'all' || sourceKey(row.source) === selectedSource),
    [itemRows, selectedSource],
  );
  const qualityPassCount = (quality.data?.checks ?? []).filter((check) => check.passed).length;
  const qualityTotalCount = quality.data?.checks?.length ?? 0;
  const confidenceExpected = gateExpected(quality.data?.checks ?? [], 'avg_confidence');
  const evaluationGates = evaluation.data?.quality_gates ?? [];
  const modelMetrics = evaluation.data?.model_metrics ?? [];
  const topKRows = evaluation.data?.topk_matrix ?? [];
  const topKHitCount = topKRows.filter((row) => row.hit).length;
  const topKHitRate = topKRows.length ? topKHitCount / topKRows.length : null;
  const riskRows = buildRecommendationRiskRows({
    summary: summary.data,
    quality: quality.data,
    checks: quality.data?.checks ?? [],
  });
  const blockingRisk = riskRows.find((row) => row.tone === 'danger');
  const strongestRisk = blockingRisk ?? riskRows.slice().sort((a, b) => b.pressure - a.pressure)[0];
  const publishVerdict = canPromote ? '可以发布' : blockingRisk ? '禁止发布' : '需要复核';
  const publishReason = canPromote
    ? '质量门禁、告警和回滚证据均允许展示当前推荐快照。'
    : blockingRisk
      ? `${blockingRisk.label} 未通过发布约束，建议先处理后再展示。`
      : '存在需要人工确认的推荐信号，建议先查看右侧解释。';
  const nextAction = canPromote ? '发布当前快照，并保留上一版用于回滚。' : '先定位风险项，必要时回滚到上一版快照。';
  const defenseAnswer = {
    explain: '前 K 命中矩阵不是商品销量图，而是离线回测样本：如果用户真实最后交互的商品出现在模型推荐的前 K 位，就记为命中。',
    gates: '评估门禁是发布条件：每一行都把实际值与阈值比较，全部通过才说明这批推荐快照具备展示依据。',
    risk: '风险结构把兜底、置信度、新鲜度、重复率和非法商品率转成发布风险；有阻断项时应回滚到上一版快照。',
  }[selectedDefenseView];
  const releaseSteps = [
    { key: 'features', label: '生成快照', detail: `${number(summary.data?.recommendation_count)} 推荐 · ${number(summary.data?.covered_sessions)} 会话`, done: Boolean(summary.data), icon: <Database size={18} /> },
    { key: 'quality', label: '质量门禁', detail: `${qualityPassCount}/${qualityTotalCount || '待生成'} 通过`, done: Boolean(quality.data?.passed), icon: <ListChecks size={18} /> },
    { key: 'publish', label: '发布/回滚', detail: canPromote ? '发布当前快照' : '准备复核或回滚', done: canPromote, icon: canPromote ? <CheckCircle2 size={18} /> : <ShieldAlert size={18} /> },
  ];
  const inspector = buildRecommendationInspector({
    selectedInspector,
    canPromote,
    status,
    fallbackRate: summary.data?.fallback_rate,
    avgConfidence: summary.data?.avg_confidence,
    sourceMix,
    qualityChecks: quality.data?.checks ?? [],
    alerts: alertRows,
    selectedSource,
  });

  const scrollToChart = (chartId: string) => {
    const target = document.querySelector(`[data-chart-id="${chartId}"]`)?.closest('.chart-panel');
    target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const cycleSourceFilter = () => {
    const sources = ['all', ...sourceMix.map((row) => row.name)];
    const nextIndex = (sources.indexOf(selectedSource) + 1) % Math.max(sources.length, 1);
    const nextSource = sources[nextIndex] ?? 'all';
    setSelectedSource(nextSource);
    setSelectedInspector('recall');
    setInspectorNotice(`已切换来源筛选为：${nextSource === 'all' ? '全部来源' : label('source', nextSource, { fallback: displayValue(nextSource) })}`);
  };

  const handleInspectorAction = (action: string) => {
    if (action.includes('切换来源') || action.includes('查看兜底来源') || action.includes('复核低置信来源')) {
      cycleSourceFilter();
      return;
    }
    if (action.includes('召回流向') || action.includes('候选召回')) {
      scrollToChart('recommendation-recall-flow');
      setInspectorNotice('已定位到“召回来源流向”，可查看候选从来源进入排序池的路径。');
      return;
    }
    if (action.includes('排序贡献')) {
      scrollToChart('recommendation-contribution');
      setInspectorNotice('已定位到“排序贡献结构”，可查看转化、新鲜度、亲和度和来源分数的贡献。');
      return;
    }
    if (action.includes('校准分层')) {
      scrollToChart('recommendation-calibration');
      setInspectorNotice('已定位到“校准分层”。当前所有候选都在高置信校准层，所以环图只有一个分组。');
      return;
    }
    if (action.includes('高置信') || action.includes('低置信')) {
      scrollToChart('recommendation-confidence');
      setInspectorNotice(itemConfidenceUniqueCount > 1 ? '已定位到高置信推荐分布。' : '当前置信度为统一门禁值，图表已改用推荐得分展示差异。');
      return;
    }
    if (action.includes('快照明细')) {
      if (snapshotDetailsRef.current) {
        snapshotDetailsRef.current.open = true;
        snapshotDetailsRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      setInspectorNotice('已展开推荐快照明细，来源筛选会影响这里的表格行。');
      return;
    }
    setInspectorNotice(`已切换到“${action}”解释视角。`);
  };

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">准实时推荐守护</span>
        <h1>准实时推荐与监控守护</h1>
        <p>用 Spark 生成可解释推荐快照，并通过质量门禁、兜底占比和回滚状态控制前端可见结果。</p>
      </section>

      {hasError ? <div className="error-banner">推荐缓存尚未生成，请先运行 Spark 刷新任务。</div> : null}
      {optionalMissing ? <div className="error-banner">候选召回与排序产物尚未生成，已保留推荐评估视图。</div> : null}

      <section className="recommendation-release-console recommendation-decision-console" aria-label="推荐守护决策中心">
        <div className="decision-console-grid">
          <article className={`decision-verdict-card tone-${canPromote ? 'success' : publishToneValue}`}>
            <div className="release-console-head">
              <div>
                <span className={`status-pill tone-${canPromote ? 'success' : publishToneValue}`}>发布判断</span>
                <h2>推荐守护决策中心</h2>
                <p>先回答“这批推荐能不能展示”，再把离线回测、质量门禁和快照明细放到下方高级证据区。</p>
              </div>
              <Sparkles size={22} />
            </div>
            <strong>{publishVerdict}</strong>
            <p>{publishReason}</p>
            <div className="decision-action-strip">
              <span>下一步</span>
              <b>{nextAction}</b>
              <small>
                {strongestRisk
                  ? canPromote
                    ? `质量压力最高但未阻断：${strongestRisk.label}，观测值 ${strongestRisk.observed}`
                    : `当前最需要关注：${strongestRisk.label}，观测值 ${strongestRisk.observed}`
                  : '等待风险证据'}
              </small>
            </div>
          </article>

          <aside className={`release-inspector tone-${inspector.tone}`} aria-label="推荐守护关键解释">
            <span>{inspector.eyebrow}</span>
            <h3>{inspector.title}</h3>
            <p>{inspector.description}</p>
            <dl>
              {inspector.metrics.map((metric) => (
                <div key={metric.label}>
                  <dt>{metric.label}</dt>
                  <dd>{metric.value}</dd>
                </div>
              ))}
            </dl>
            <div className="release-inspector-actions">
              {inspector.actions.map((action) => (
                <button type="button" key={action} onClick={() => handleInspectorAction(action)}>{action}</button>
              ))}
            </div>
            <p className="release-inspector-notice">{inspectorNotice}</p>
          </aside>
        </div>

        <div className="decision-kpi-row" aria-label="推荐守护关键指标">
          <button type="button" className="release-kpi-card" onClick={() => setSelectedInspector('recall')}>
            <span>推荐覆盖</span>
            <strong>{number(summary.data?.recommendation_count)}</strong>
            <small>覆盖 {number(summary.data?.covered_sessions)} 个会话</small>
          </button>
          <button type="button" className={`release-kpi-card tone-${fallbackTone}`} onClick={() => setSelectedInspector('fallback')}>
            <span>兜底占比</span>
            <strong>{percent(summary.data?.fallback_rate)}</strong>
            <small>越高越说明个性化不足</small>
          </button>
          <button type="button" className={`release-kpi-card tone-${confidenceTone}`} onClick={() => setSelectedInspector('confidence')}>
            <span>平均置信度</span>
            <strong>{percent(summary.data?.avg_confidence)}</strong>
            <small>门禁 {typeof confidenceExpected === 'number' ? percent(confidenceExpected) : score(confidenceExpected)}</small>
          </button>
        </div>

        <div className="decision-evidence-path" aria-label="推荐守护三步证据链">
          {releaseSteps.map((step, index) => (
            <button
              type="button"
              className={`release-step${step.done ? ' is-done' : ' is-review'}${selectedInspector === step.key ? ' is-active' : ''}`}
              key={step.key}
              onClick={() => setSelectedInspector(step.key)}
            >
              <span className="release-step-index">{index + 1}</span>
              <span className="release-step-icon">{step.icon}</span>
              <strong>{step.label}</strong>
              <small>{step.detail}</small>
            </button>
          ))}
        </div>
      </section>

      <details className="recommendation-evidence-disclosure">
        <summary>
          <span>展开离线评估、图表证据和推荐快照</span>
          <small>高级指标用于答辩追问或排查风险，默认不打断首屏发布判断。</small>
        </summary>
        <div className="recommendation-evidence-stack">
          <section className="release-filter-panel recommendation-source-filter" aria-label="推荐来源与门禁筛选">
            <div className="release-filter-title">
              <GitBranch size={18} />
              <div>
                <strong>来源筛选与门禁快捷检查</strong>
                <span>只影响下方快照明细和解释器，不改变后端推荐结果。</span>
              </div>
            </div>
            <div className="release-filter-chips" aria-label="推荐来源筛选">
              <button
                type="button"
                className={selectedSource === 'all' ? 'is-active' : ''}
                  onClick={() => {
                    setSelectedSource('all');
                    setSelectedInspector('recall');
                    setInspectorNotice('已恢复为全部来源，下面快照表展示全部 50 条推荐。');
                  }}
                >
                全部 {number(itemRows.length)}
              </button>
              {sourceMix.map((row) => (
                <button
                  type="button"
                  className={selectedSource === row.name ? 'is-active' : ''}
                  key={row.name}
                  onClick={() => {
                    setSelectedSource(row.name);
                    setSelectedInspector('recall');
                    setInspectorNotice(`已筛选为 ${label('source', row.name, { fallback: displayValue(row.name) })}，下面快照表只展示该来源。`);
                  }}
                >
                  {label('source', row.name, { fallback: displayValue(row.name) })} {number(row.value)}
                </button>
              ))}
            </div>
            <div className="release-gate-grid" aria-label="质量门禁快捷检查">
              {(quality.data?.checks ?? []).slice(0, 6).map((check) => (
                <button
                  type="button"
                  className={`release-gate-card tone-${check.passed ? 'success' : 'danger'}`}
                  key={check.name}
                  onClick={() => setSelectedInspector(check.name)}
                >
                  <span>{fieldLabel(check.name)}</span>
                  <strong>{check.passed ? '通过' : '失败'}</strong>
                  <small>{score(check.actual)} {check.operator} {score(check.expected)}</small>
                </button>
              ))}
            </div>
          </section>

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

      <section className="recommendation-defense-console" aria-label="推荐评估答辩解释区">
        <div className="defense-console-head">
          <div>
            <span className="eyebrow">答辩解释区</span>
            <h2>模型效果、发布门禁与风险依据</h2>
            <p>把离线回测、质量阈值和回滚证据放在同一条证据链中，回答“为什么这批推荐可以展示”。</p>
          </div>
          <div className="defense-tabs" aria-label="推荐评估解释视角">
            {[
              ['explain', '评估解释'],
              ['gates', '门禁明细'],
              ['risk', '风险下钻'],
            ].map(([key, text]) => (
              <button
                type="button"
                className={selectedDefenseView === key ? 'is-active' : ''}
                key={key}
                onClick={() => setSelectedDefenseView(key as 'explain' | 'gates' | 'risk')}
              >
                {text}
              </button>
            ))}
          </div>
        </div>

        <div className="defense-answer-strip">
          <strong>老师可能会问：</strong>
          <span>{defenseAnswer}</span>
        </div>

        <div className="defense-metric-strip" aria-label="推荐评估核心指标释义">
          <button type="button" title="Precision@K = 推荐前 K 个商品中命中的比例。">
            <span>Precision@K</span>
            <strong>{topEvaluationModel ? percent(topEvaluationModel.precision_at_k) : '待生成'}</strong>
            <small>前 K 推荐准确性</small>
          </button>
          <button type="button" title="Recall@K = 真实目标商品被前 K 推荐覆盖的比例。">
            <span>Recall@K</span>
            <strong>{topEvaluationModel ? percent(topEvaluationModel.recall_at_k) : '待生成'}</strong>
            <small>目标覆盖完整度</small>
          </button>
          <button type="button" title="NDCG@K 会给更靠前命中的商品更高权重。">
            <span>NDCG@K</span>
            <strong>{topEvaluationModel ? percent(topEvaluationModel.ndcg_at_k) : '待生成'}</strong>
            <small>排序位置质量</small>
          </button>
          <button type="button" title="命中样本数来自离线回测 top-k_matrix。">
            <span>Top-K 样本</span>
            <strong>{number(topKRows.length)}</strong>
            <small>命中 {topKHitRate == null ? '待生成' : percent(topKHitRate)}</small>
          </button>
        </div>

        <div className="defense-evaluation-grid">
          <article className="data-panel defense-panel">
            <div className="panel-title">
              <div>
                <h2>前 K 命中矩阵</h2>
                <p>物理量：推荐排序位置。绿色表示真实目标商品被前 K 推荐命中，红色表示未命中。</p>
              </div>
              <span className="status-pill tone-success">命中 {number(topKHitCount)}</span>
            </div>
            <RecommendationTopKMatrix rows={topKRows} />
            <div className="defense-legend">
              <span><i className="tone-hit" />命中：真实后续行为商品出现在推荐列表</span>
              <span><i className="tone-miss" />未命中：前 K 未覆盖真实目标</span>
            </div>
          </article>

          <article className="data-panel defense-panel">
            <div className="panel-title">
              <div>
                <h2>评估门禁</h2>
                <p>物理量：离线回测是否可用、基线是否可比、质量阈值是否满足发布标准。</p>
              </div>
              <ShieldCheck size={20} />
            </div>
            <div className="gate-table" role="table" aria-label="推荐评估门禁表">
              <div className="gate-table-head" role="row">
                <span>门禁</span>
                <span>观测值</span>
                <span>阈值</span>
                <span>结论</span>
              </div>
              {evaluationGates.map((check) => (
                <button
                  type="button"
                  className={`gate-row tone-${check.passed ? 'success' : 'danger'}`}
                  key={check.name}
                  onClick={() => setSelectedInspector(check.name)}
                >
                  <span>{fieldLabel(check.name)}</span>
                  <strong>{formatRecommendationMetric(check.name, check.actual)}</strong>
                  <span>{check.operator} {formatRecommendationMetric(check.name, check.expected)}</span>
                  <em>{check.passed ? '通过' : '阻断'}</em>
                </button>
              ))}
              {evaluationGates.length === 0 ? <p className="empty-copy">等待离线评估门禁。</p> : null}
            </div>
          </article>
        </div>

        <div className="defense-risk-grid">
          <ChartPanel
            title="发布风险结构"
            subtitle="用门禁压力归一化展示风险，避免新鲜度天数压扁其他比例指标"
            option={horizontalBarOption(
              riskRows.map((row) => ({ name: row.label, value: row.pressure })),
              '门禁压力 %',
              '#f59e0b',
            )}
            summary={`当前重点风险：${riskRows.find((row) => row.tone === 'danger')?.label ?? '无阻断项'}。`}
          />
          <article className="data-panel defense-panel risk-detail-panel">
            <div className="panel-title">
              <div>
                <h2>风险明细表</h2>
                <p>补充图表右侧的数值依据，说明每个风险项如何影响发布或回滚。</p>
              </div>
              <ShieldAlert size={20} />
            </div>
            <div className="risk-detail-table" role="table" aria-label="推荐发布风险明细表">
              <div className="risk-detail-head" role="row">
                <span>指标</span>
                <span>观测值</span>
                <span>阈值</span>
                <span>决策</span>
              </div>
              {riskRows.map((row) => (
                <button
                  type="button"
                  className={`risk-detail-row tone-${row.tone}`}
                  key={row.key}
                  title={row.quantity}
                  onClick={() => setSelectedInspector(row.key)}
                >
                  <span>
                    <strong>{row.label}</strong>
                    <small>{row.quantity}</small>
                  </span>
                  <em>{row.observed}</em>
                  <span>{row.threshold}</span>
                  <b>{row.decision}</b>
                </button>
              ))}
            </div>
          </article>
        </div>
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
          subtitle="展示进入排序阶段的高分候选，横轴自动放大到当前分数区间"
          chartId="recommendation-ranker-score"
          option={rangedHorizontalBarOption(rankerScoreTop, '排序分数 %', '#65b8ff')}
          isLoading={candidates.isLoading}
          isEmpty={!rankerScoreTop.length}
          annotations={[
            { label: '唯一分数', value: number(candidateRankerUniqueCount), tone: candidateRankerUniqueCount > 1 ? 'success' : 'warning' },
            { label: '显示口径', value: '动态横轴', tone: 'info' },
          ]}
          summary={
            topRankedCandidate
              ? `${topRankedCandidate.name} 当前排序分数最高，为 ${topRankedCandidate.value.toFixed(2)}%，当前排序器为 ${label('model', topRankerModel?.name)}。`
              : '等待排序分数。'
          }
        />
        <ChartPanel
          title="校准分层"
          subtitle="按置信度分层观察排序器是否过度集中"
          chartId="recommendation-calibration"
          option={donutOption(candidateCalibrationMix, '候选数量')}
          isLoading={candidates.isLoading}
          isEmpty={!candidateCalibrationMix.length}
          annotations={[
            { label: '校准层数量', value: number(candidateCalibrationUniqueCount), tone: candidateCalibrationUniqueCount > 1 ? 'success' : 'warning' },
            { label: '解释', value: candidateCalibrationUniqueCount <= 1 ? '当前全在同一层' : '存在分层差异', tone: candidateCalibrationUniqueCount <= 1 ? 'warning' : 'success' },
          ]}
          summary={
            topCalibration
              ? candidateCalibrationUniqueCount <= 1
                ? `${label('risk', topCalibration.name)}校准层包含全部候选，共 ${number(topCalibration.value)} 条；这表示当前校准规则没有把候选拆成多层。`
                : `${label('risk', topCalibration.name)}校准层当前最多，共 ${number(topCalibration.value)} 条。`
              : '等待校准分层。'
          }
        />
        <ChartPanel
          title="排序贡献结构"
          subtitle="用转化、新鲜度、图谱亲和和来源置信解释排序结果"
          chartId="recommendation-contribution"
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
          title={confidenceChartTitle}
          subtitle={confidenceChartSubtitle}
          chartId="recommendation-confidence"
          option={itemConfidenceUniqueCount > 1 ? horizontalBarOption(confidenceChartRows, confidenceChartMetric, '#56d27b') : rangedHorizontalBarOption(confidenceChartRows, confidenceChartMetric, '#56d27b')}
          annotations={[
            { label: '置信度唯一值', value: number(itemConfidenceUniqueCount), tone: itemConfidenceUniqueCount > 1 ? 'success' : 'warning' },
            { label: '当前图表', value: itemConfidenceUniqueCount > 1 ? '置信度' : '推荐得分', tone: 'info' },
          ]}
          summary={
            itemConfidenceUniqueCount > 1
              ? topConfidence
                ? `${topConfidence.name} 置信度最高，为 ${topConfidence.value.toFixed(1)}%。`
                : '等待推荐置信度数据。'
              : confidenceChartRows[0]
                ? `当前所有推荐置信度均为 ${percent(itemRows[0]?.confidence)}，所以这里改用推荐得分展示差异；${confidenceChartRows[0].name} 得分最高，为 ${confidenceChartRows[0].value.toFixed(2)}%。`
                : '等待推荐得分数据。'
          }
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

      <details className="detail-table-disclosure" ref={snapshotDetailsRef}>
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
                {filteredItemRows.map((row) => (
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
                {filteredItemRows.length === 0 ? (
                  <tr>
                    <td colSpan={9}>{itemRows.length ? '当前筛选下没有推荐快照' : '等待推荐快照'}</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </details>
        </div>
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
  const visibleRows = rows.slice(0, 12);
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
