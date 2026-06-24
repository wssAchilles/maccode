import { useMemo, useState } from 'react';
import { Boxes, Clock3, DatabaseZap, Eye, GitBranch, Layers3, PackageSearch, ShieldCheck, Users } from 'lucide-react';
import {
  useFeatureMartCategories,
  useFeatureMartFeatures,
  useFeatureMartFreshness,
  useFeatureMartPartitions,
  useFeatureMartProducts,
  useFeatureMartQuality,
  useFeatureMartReadiness,
  useFeatureMartSummary,
  useFeatureMartUsers,
} from '../api/hooks';
import { ChartPanel, type DashboardChartOption } from '../components/ChartPanel';
import { fieldLabel, label, statusLabel } from '../i18n/displayText';
import type { FeatureMartCategory, FeatureMartFeature, FeatureMartProduct, FeatureMartReadiness, FeatureMartUser, NamedValue } from '../types/api';

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : '待生成';
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(2)}%` : '待生成';
}

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : '待生成';
}

function hours(value?: number | null) {
  if (typeof value !== 'number') {
    return '待生成';
  }
  return value >= 24 ? `${(value / 24).toFixed(1)} 天` : `${value.toFixed(1)} 小时`;
}

function statusTone(status?: string) {
  if (status === 'passed' || status === 'written') return 'succeeded';
  if (status === 'failed' || status === 'stale') return 'failed';
  return 'queued';
}

function grainLabel(value: string) {
  return value
    .replace(/dt/g, '日期')
    .replace(/product_id/g, '商品')
    .replace(/category_level1/g, '类目')
    .replace(/user_id/g, '用户')
    .replace(/\+/g, ' + ');
}

function clamp01(value: number) {
  return Math.max(0, Math.min(1, value));
}

function featureGrainBucket(grain: string) {
  if (grain.includes('product_id')) return '商品粒度字段';
  if (grain.includes('category_level1')) return '类目粒度字段';
  if (grain.includes('user_id')) return '用户粒度字段';
  return '运行审计字段';
}

function readinessRows(data?: FeatureMartReadiness, features: FeatureMartFeature[] = []): NamedValue[] {
  const readinessFeatures =
    features.length >= (data?.features.length ?? 0)
      ? features.map((feature) => ({ grain: feature.grain, status: 'ready' }))
      : data?.features ?? [];
  const byGrain = new Map<string, number>();
  readinessFeatures
    .filter((feature) => feature.status === 'ready')
    .forEach((feature) => {
      const bucket = featureGrainBucket(feature.grain);
      byGrain.set(bucket, (byGrain.get(bucket) ?? 0) + 1);
    });

  return Array.from(byGrain.entries())
    .map(([name, value]) => ({ name, value }))
    .filter((row) => row.value > 0);
}

function qualityScoreRows({
  readyFeatures,
  totalFeatures,
  writtenPartitions,
  expectedPartitions,
  lateRate,
  freshnessLagHours,
  maxFreshnessLagHours,
  quarantinedRate,
}: {
  readyFeatures: number;
  totalFeatures: number;
  writtenPartitions?: number;
  expectedPartitions?: number;
  lateRate?: number | null;
  freshnessLagHours?: number | null;
  maxFreshnessLagHours?: number | null;
  quarantinedRate?: number | null;
}): NamedValue[] {
  return [
    {
      name: '字段就绪率',
      value: totalFeatures > 0 ? readyFeatures / totalFeatures : 0,
    },
    {
      name: '分区覆盖率',
      value: expectedPartitions && expectedPartitions > 0 ? (writtenPartitions ?? 0) / expectedPartitions : 0,
    },
    {
      name: '迟到控制',
      value: typeof lateRate === 'number' ? 1 - lateRate : 0,
    },
    {
      name: '新鲜度余量',
      value:
        typeof freshnessLagHours === 'number' && typeof maxFreshnessLagHours === 'number' && maxFreshnessLagHours > 0
          ? 1 - freshnessLagHours / maxFreshnessLagHours
          : 0,
    },
    {
      name: '隔离控制',
      value: typeof quarantinedRate === 'number' ? 1 - quarantinedRate : 0,
    },
  ].map((row) => ({ ...row, value: clamp01(row.value) }));
}

const featureChartTextStyle = {
  fontFamily: 'Inter, "Microsoft YaHei", system-ui, sans-serif',
  color: '#dbe5ee',
};

function featureReadinessOption(rows: NamedValue[]): DashboardChartOption {
  return {
    color: ['#39d0c8', '#65b8ff', '#a78bfa', '#f59e0b'],
    textStyle: featureChartTextStyle,
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} 个 ({d}%)',
    },
    legend: {
      bottom: 0,
      left: 'center',
      itemWidth: 12,
      itemHeight: 12,
      textStyle: { color: '#9aa7b7', fontSize: 12 },
    },
    series: [
      {
        name: '字段粒度',
        type: 'pie',
        radius: ['56%', '72%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        label: {
          show: true,
          color: '#dbe5ee',
          fontSize: 12,
          formatter: '{b}\n{d}%',
        },
        labelLine: {
          length: 8,
          length2: 8,
        },
        data: rows,
      },
    ],
  };
}

function featureQualityOption(rows: NamedValue[]): DashboardChartOption {
  const reversedRows = [...rows].reverse();
  return {
    color: ['#56d27b', '#f59e0b', '#fb7185'],
    textStyle: featureChartTextStyle,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (rawParams) => {
        const params = Array.isArray(rawParams) ? rawParams[0] : rawParams;
        const item = params as { name?: string; value?: number } | undefined;
        return `${item?.name ?? '质量健康度'}：${((Number(item?.value ?? 0)) * 100).toFixed(1)}%`;
      },
    },
    grid: { left: 118, right: 48, top: 18, bottom: 28 },
    xAxis: {
      type: 'value',
      min: 0,
      max: 1,
      splitNumber: 2,
      axisLabel: {
        color: '#8fa1b4',
        formatter: (value: number) => `${Math.round(value * 100)}%`,
      },
      splitLine: { lineStyle: { color: 'rgba(101, 184, 255, 0.18)' } },
    },
    yAxis: {
      type: 'category',
      data: reversedRows.map((row) => row.name),
      axisLabel: {
        color: '#b8c4d4',
        width: 108,
        overflow: 'truncate',
      },
      axisLine: { lineStyle: { color: 'rgba(101, 184, 255, 0.22)' } },
      axisTick: { show: false },
    },
    series: [
      {
        name: '健康度',
        type: 'bar',
        barWidth: 16,
        data: reversedRows.map((row) => ({
          value: row.value,
          itemStyle: {
            color: row.value >= 0.9 ? '#56d27b' : row.value >= 0.6 ? '#f59e0b' : '#fb7185',
            borderRadius: [0, 8, 8, 0],
          },
          label: {
            formatter: `${(row.value * 100).toFixed(1)}%`,
          },
        })),
        label: {
          show: true,
          position: 'right',
          color: '#dbe5ee',
          fontWeight: 700,
        },
      },
    ],
  };
}

const lineageLayer: Record<string, number> = {
  raw_events: 0,
  cleaned_events: 1,
  daily_product_behavior: 2,
  daily_category_behavior: 2,
  feature_mart: 3,
  recommendations_forecasting_anomaly: 4,
};

function featureLineageOption(lineage: FeatureMartReadiness['lineage'] = []): DashboardChartOption {
  const nodeIds = Array.from(new Set(lineage.flatMap((edge) => [edge.from, edge.to])));
  const layers = new Map<number, string[]>();
  nodeIds.forEach((nodeId) => {
    const layer = lineageLayer[nodeId] ?? 2;
    layers.set(layer, [...(layers.get(layer) ?? []), nodeId]);
  });
  const nodes = nodeIds.map((nodeId) => {
    const layer = lineageLayer[nodeId] ?? 2;
    const peers = layers.get(layer) ?? [nodeId];
    const peerIndex = peers.indexOf(nodeId);
    const yOffset = peers.length === 1 ? 0 : (peerIndex - (peers.length - 1) / 2) * 56;
    return {
      id: nodeId,
      name: label('lineage', nodeId, { fallback: nodeId }),
      x: 58 + layer * 128,
      y: 116 + yOffset,
      symbolSize: layer === 0 || layer >= 3 ? 42 : 38,
      value: layer,
      itemStyle: {
        color: ['#39d0c8', '#65b8ff', '#f59e0b', '#a78bfa', '#56d27b'][Math.min(layer, 4)],
      },
      label: { show: true },
    };
  });
  const links = lineage.map((edge) => ({
    source: label('lineage', edge.from, { fallback: edge.from }),
    target: label('lineage', edge.to, { fallback: edge.to }),
    relation: label('lineage', edge.relation, { fallback: edge.relation }),
    lineStyle: { curveness: 0.12, opacity: 0.62 },
  }));

  return {
    tooltip: {
      trigger: 'item',
      formatter: (rawParams) => {
        const params = Array.isArray(rawParams) ? rawParams[0] : rawParams;
        const item = params as { data?: { source?: string; target?: string; relation?: string; name?: string }; dataType?: string; name?: string } | undefined;
        if (item?.dataType === 'edge') {
          return [`<strong>${item.data?.relation ?? '血缘关系'}</strong>`, `${item.data?.source ?? '来源'} 至 ${item.data?.target ?? '目标'}`].join('<br/>');
        }
        return item?.data?.name ?? item?.name ?? '特征血缘节点';
      },
    },
    aria: {
      enabled: true,
      description: `特征血缘图，展示 ${nodes.length} 个节点和 ${links.length} 条产物依赖边。`,
    },
    series: [
      {
        name: '特征血缘',
        type: 'graph',
        layout: 'none',
        data: nodes,
        links,
        roam: true,
        draggable: true,
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 8],
        label: {
          show: true,
          position: 'bottom',
          color: '#dbe5ee',
          fontSize: 11,
          width: 82,
          overflow: 'truncate',
        },
        lineStyle: {
          color: '#8fb3cf',
          width: 1.8,
          curveness: 0.12,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 4, opacity: 0.9 },
        },
      },
    ],
  };
}

type FeatureMartView = 'product' | 'category' | 'user';

type FeatureCoverageCard = {
  view: FeatureMartView;
  title: string;
  subtitle: string;
  rows: number;
  entityCount: number;
  revenue: number;
  purchases: number;
  featureCount: number;
};

const viewCopy: Record<FeatureMartView, { title: string; unit: string; icon: typeof Boxes; empty: string }> = {
  product: {
    title: '商品粒度',
    unit: '商品',
    icon: Boxes,
    empty: '当前筛选下没有商品特征样本。',
  },
  category: {
    title: '类目粒度',
    unit: '类目',
    icon: Layers3,
    empty: '当前筛选下没有类目聚合样本。',
  },
  user: {
    title: '用户粒度',
    unit: '用户',
    icon: Users,
    empty: '当前筛选下没有用户特征样本。',
  },
};

function sum<T>(rows: T[], pick: (row: T) => number | null | undefined) {
  return rows.reduce((total, row) => total + (pick(row) ?? 0), 0);
}

function uniqueCount<T>(rows: T[], pick: (row: T) => string | number | null | undefined) {
  return new Set(rows.map((row) => pick(row)).filter(Boolean)).size;
}

function featureBelongsToView(feature: FeatureMartFeature, view: FeatureMartView) {
  if (view === 'product') return feature.grain.includes('product_id') || feature.feature_name.includes('product');
  if (view === 'category') return feature.grain.includes('category_level1') || feature.feature_name.includes('category');
  return feature.grain.includes('user_id') || feature.feature_name.includes('user');
}

function productCategory(row: FeatureMartProduct | FeatureMartCategory | FeatureMartUser) {
  if ('category_level1' in row) return row.category_level1 || '未知';
  return row.preferred_category_level1 || '未知';
}

function buildCoverageCards(
  products: FeatureMartProduct[],
  categories: FeatureMartCategory[],
  users: FeatureMartUser[],
  features: FeatureMartFeature[],
): FeatureCoverageCard[] {
  return [
    {
      view: 'product',
      title: '商品特征层',
      subtitle: '按日期 x 商品聚合浏览、加购、购买、价格和转化率。',
      rows: products.length,
      entityCount: uniqueCount(products, (row) => row.product_id),
      revenue: sum(products, (row) => row.revenue),
      purchases: sum(products, (row) => row.purchases),
      featureCount: features.filter((feature) => featureBelongsToView(feature, 'product')).length,
    },
    {
      view: 'category',
      title: '类目特征层',
      subtitle: '按日期 x 一级类目聚合需求规模、成交额和转化率。',
      rows: categories.length,
      entityCount: uniqueCount(categories, (row) => row.category_level1),
      revenue: sum(categories, (row) => row.revenue),
      purchases: sum(categories, (row) => row.purchases),
      featureCount: features.filter((feature) => featureBelongsToView(feature, 'category')).length,
    },
    {
      view: 'user',
      title: '用户特征层',
      subtitle: '按日期 x 用户聚合活跃、兴趣偏好、购买和价值信号。',
      rows: users.length,
      entityCount: uniqueCount(users, (row) => row.user_id),
      revenue: sum(users, (row) => row.revenue),
      purchases: sum(users, (row) => row.purchases),
      featureCount: features.filter((feature) => featureBelongsToView(feature, 'user')).length,
    },
  ];
}

function buildCategoryCoverage(
  rows: Array<FeatureMartProduct | FeatureMartCategory | FeatureMartUser>,
) {
  const map = new Map<string, { name: string; rows: number; revenue: number; purchases: number; users: number }>();
  rows.forEach((row) => {
    const name = productCategory(row);
    const current = map.get(name) ?? { name, rows: 0, revenue: 0, purchases: 0, users: 0 };
    current.rows += 1;
    current.revenue += 'revenue' in row ? row.revenue : 0;
    current.purchases += 'purchases' in row ? row.purchases : 0;
    current.users += 'unique_users' in row ? row.unique_users : 'user_id' in row ? 1 : 0;
    map.set(name, current);
  });
  return Array.from(map.values()).sort((a, b) => b.rows - a.rows || b.revenue - a.revenue);
}

function filterByCategory<T extends FeatureMartProduct | FeatureMartCategory | FeatureMartUser>(rows: T[], category: string) {
  return category === 'all' ? rows : rows.filter((row) => productCategory(row) === category);
}

function aggregateRows(rows: Array<FeatureMartProduct | FeatureMartCategory | FeatureMartUser>) {
  return {
    rows: rows.length,
    revenue: sum(rows, (row) => row.revenue),
    purchases: sum(rows, (row) => row.purchases),
  };
}

function TablePreviewIcon({ view }: { view: FeatureMartView }) {
  const Icon = viewCopy[view].icon;
  return <Icon size={19} />;
}

export function FeatureMartPage() {
  const [selectedView, setSelectedView] = useState<FeatureMartView>('product');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const summary = useFeatureMartSummary();
  const freshness = useFeatureMartFreshness();
  const quality = useFeatureMartQuality();
  const partitions = useFeatureMartPartitions();
  const features = useFeatureMartFeatures();
  const readiness = useFeatureMartReadiness();
  const products = useFeatureMartProducts(50);
  const categories = useFeatureMartCategories(50);
  const users = useFeatureMartUsers(50);
  const hasError =
    summary.isError ||
    freshness.isError ||
    quality.isError ||
    partitions.isError ||
    products.isError ||
    categories.isError ||
    users.isError;
  const featureRows = features.data ?? [];
  const productRows = products.data ?? [];
  const categoryRows = categories.data ?? [];
  const userRows = users.data ?? [];
  const readyFeatureCount = readiness.data?.ready_features ?? 0;
  const totalFeatureCount = readiness.data?.total_features ?? featureRows.length;
  const readinessChartRows = readinessRows(readiness.data, featureRows);
  const readinessCheckRows = qualityScoreRows({
    readyFeatures: readyFeatureCount,
    totalFeatures: totalFeatureCount,
    writtenPartitions: summary.data?.partitions.written,
    expectedPartitions: summary.data?.partitions.expected,
    lateRate: freshness.data?.late_rate,
    freshnessLagHours: freshness.data?.freshness_lag_hours ?? summary.data?.freshness.freshness_lag_hours,
    maxFreshnessLagHours: freshness.data?.max_freshness_lag_hours,
    quarantinedRate: quality.data?.quarantined_rate,
  });
  const lineageRows = readiness.data?.lineage ?? [];
  const coverageCards = useMemo(
    () => buildCoverageCards(productRows, categoryRows, userRows, featureRows),
    [categoryRows, featureRows, productRows, userRows],
  );
  const activeRows = selectedView === 'product' ? productRows : selectedView === 'category' ? categoryRows : userRows;
  const allLayerRows = useMemo(
    () => [...productRows, ...categoryRows, ...userRows],
    [categoryRows, productRows, userRows],
  );
  const categoryCoverage = useMemo(() => buildCategoryCoverage(activeRows), [activeRows]);
  const allLayerCategoryCoverage = useMemo(() => buildCategoryCoverage(allLayerRows), [allLayerRows]);
  const maxCategoryRows = Math.max(1, ...categoryCoverage.map((item) => item.rows));
  const filteredProducts = useMemo(() => filterByCategory(productRows, selectedCategory), [productRows, selectedCategory]);
  const filteredCategories = useMemo(() => filterByCategory(categoryRows, selectedCategory), [categoryRows, selectedCategory]);
  const filteredUsers = useMemo(() => filterByCategory(userRows, selectedCategory), [userRows, selectedCategory]);
  const selectedFeatures = featureRows.filter((feature) => featureBelongsToView(feature, selectedView));
  const selectedRows =
    selectedView === 'product' ? filteredProducts : selectedView === 'category' ? filteredCategories : filteredUsers;
  const selectedSampleMetrics = aggregateRows(selectedRows);
  const allLayerSelectedCoverage = allLayerCategoryCoverage.find((item) => item.name === selectedCategory);
  const topCategory = categoryCoverage[0]?.name ?? '待生成';
  const failedCheckCount = (readiness.data?.checks ?? []).filter((check) => !check.passed).length;
  const lowestQualityScore = readinessCheckRows.length ? Math.min(...readinessCheckRows.map((row) => row.value)) : 0;
  const featureGrainCount = new Set(featureRows.map((feature) => feature.grain)).size;

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">行为特征集市</span>
        <h1>湖仓级行为事实与特征层</h1>
        <p>把真实 Kaggle 行为日志沉淀为可重跑、可审计、可被推荐和实验复用的日级事实/特征产物。</p>
      </section>

      {hasError ? (
        <div className="error-banner" role="alert">
          特征集市缓存尚未生成，请先运行 Spark 刷新任务。
        </div>
      ) : null}

      <section className="ops-command-band">
        <div>
          <span aria-label={`质量状态：${statusLabel(summary.data?.quality_status)}`} className={`status-pill tone-${statusTone(summary.data?.quality_status)}`}>
            {statusLabel(summary.data?.quality_status)}
          </span>
          <h2>特征集市契约 v1</h2>
          <p>
            {summary.data?.run_id ?? '等待特征集市'} · {summary.data?.date_range.min_dt ?? '待生成'} 至{' '}
            {summary.data?.date_range.max_dt ?? '待生成'}
          </p>
        </div>
        <DatabaseZap size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>写入分区</span>
          <strong>{number(summary.data?.partitions.written)}</strong>
          <small>{number(summary.data?.partitions.expected)} 个预期分区</small>
        </article>
        <article className="metric-card">
          <span>去重事件</span>
          <strong>{number(summary.data?.deduped_event_rows)}</strong>
          <small>{number(summary.data?.cleaned_rows)} 行清洗后数据</small>
        </article>
        <article className="metric-card">
          <span>新鲜度承诺</span>
          <strong>{statusLabel(freshness.data?.sla_status ?? summary.data?.freshness.sla_status)}</strong>
          <small>延迟 {hours(freshness.data?.freshness_lag_hours ?? summary.data?.freshness.freshness_lag_hours)}</small>
        </article>
        <article className="metric-card tone-warning">
          <span>迟到数据</span>
          <strong>{number(freshness.data?.late_rows)}</strong>
          <small>{percent(freshness.data?.late_rate)} 迟到率</small>
        </article>
      </section>

      <section className="feature-mart-workbench" aria-label="特征集市覆盖工作台">
        <div className="feature-mart-workbench-head">
          <div>
            <span className="eyebrow">Category Coverage Workbench</span>
            <h2>每种特征层都有入口，点击后联动类目、字典和样本</h2>
            <p>先看商品、类目、用户三类可复用特征产物，再按业务类目钻取代表样本，不把全量明细直接堆到页面。</p>
          </div>
          <div className="feature-mart-scope-card">
            <span>当前解释对象</span>
            <strong>{viewCopy[selectedView].title}</strong>
            <small>{selectedCategory === 'all' ? '全部业务类目' : selectedCategory}</small>
          </div>
        </div>

        <div className="feature-coverage-grid">
          {coverageCards.map((card) => {
            const meta = viewCopy[card.view];
            const Icon = meta.icon;
            return (
              <button
                className={`feature-coverage-card ${selectedView === card.view ? 'is-active' : ''}`}
                key={card.view}
                type="button"
                onClick={() => setSelectedView(card.view)}
              >
                <span className="feature-card-icon">
                  <Icon size={19} />
                </span>
                <span className="feature-card-copy">
                  <strong>{card.title}</strong>
                  <small>{card.subtitle}</small>
                </span>
                <span className="feature-card-metrics">
                  <span>
                    {number(card.entityCount)}
                    <small>{meta.unit}</small>
                  </span>
                  <span>
                    {number(card.rows)}
                    <small>样本行</small>
                  </span>
                  <span>
                    {number(card.featureCount)}
                    <small>字段</small>
                  </span>
                </span>
              </button>
            );
          })}
        </div>

        <div className="feature-category-workspace">
          <article className="feature-category-panel">
            <div className="panel-title compact">
              <div>
                <h2>业务类目覆盖</h2>
                <p>卡片按当前选中的特征粒度统计，点击后下方代表样本表使用同一口径。</p>
              </div>
              <PackageSearch size={20} />
            </div>
            <div className="feature-category-strip" role="list" aria-label="业务类目筛选">
              <button
                className={`feature-category-chip ${selectedCategory === 'all' ? 'is-active' : ''}`}
                type="button"
                onClick={() => setSelectedCategory('all')}
              >
                <strong>全部类目</strong>
                <span>{viewCopy[selectedView].title} · {number(categoryCoverage.length)} 个类目入口</span>
                <i style={{ width: '100%' }} />
              </button>
              {categoryCoverage.map((item) => (
                <button
                  className={`feature-category-chip ${selectedCategory === item.name ? 'is-active' : ''}`}
                  key={item.name}
                  type="button"
                  onClick={() => setSelectedCategory(item.name)}
                >
                  <strong>{item.name}</strong>
                  <span>
                    当前层 {number(item.rows)} 行 · {number(item.purchases)} 次购买
                  </span>
                  <i style={{ width: `${Math.max(6, (item.rows / maxCategoryRows) * 100)}%` }} />
                </button>
              ))}
            </div>
          </article>

          <aside className="feature-explain-panel">
            <div className="panel-title compact">
              <div>
                <h2>当前钻取解释</h2>
                <p>点击左侧粒度或类目，这里同步说明你正在查看哪种特征产物。</p>
              </div>
              <Eye size={19} />
            </div>
            <div className="feature-explain-metrics">
              <span>
                <small>当前样本</small>
                <strong>{number(selectedSampleMetrics.rows)}</strong>
              </span>
              <span>
                <small>成交额</small>
                <strong>{money(selectedSampleMetrics.revenue)}</strong>
              </span>
              <span>
                <small>购买量</small>
                <strong>{number(selectedSampleMetrics.purchases)}</strong>
              </span>
            </div>
            <div className="feature-explain-copy">
              <strong>{selectedCategory === 'all' ? `最高覆盖类目：${topCategory}` : `当前类目：${selectedCategory}`}</strong>
              <p>
                {viewCopy[selectedView].title}用于把原始行为日志转成下游可复用字段；当前类目卡片、右侧解释和下方样本表现在都使用同一粒度口径。
                {selectedCategory !== 'all' && allLayerSelectedCoverage
                  ? ` 该类目全特征层合计为 ${number(allLayerSelectedCoverage.rows)} 行、${number(allLayerSelectedCoverage.purchases)} 次购买，仅作为背景参考。`
                  : ''}
              </p>
            </div>
          </aside>
        </div>

        <div className="feature-preview-grid">
          <article className="feature-preview-panel">
            <div className="panel-title compact">
              <div>
                <h2>{viewCopy[selectedView].title}代表样本</h2>
                <p>只展示当前筛选的前 12 行，完整缓存仍可在下方折叠表查看。</p>
              </div>
              <TablePreviewIcon view={selectedView} />
            </div>
            <div className="table-scroll feature-sample-scroll">
              {selectedView === 'product' ? (
                <table aria-label="商品粒度代表样本">
                  <thead>
                    <tr>
                      <th>日期</th>
                      <th>商品</th>
                      <th>类目</th>
                      <th>品牌</th>
                      <th>浏览</th>
                      <th>购买</th>
                      <th>成交额</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredProducts.slice(0, 12).map((row) => (
                      <tr key={`${row.dt}-${row.product_id}`}>
                        <td>{row.dt}</td>
                        <td>{row.product_id}</td>
                        <td>{row.category_level1}</td>
                        <td>{row.brand}</td>
                        <td>{number(row.views)}</td>
                        <td>{number(row.purchases)}</td>
                        <td>{money(row.revenue)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : selectedView === 'category' ? (
                <table aria-label="类目粒度代表样本">
                  <thead>
                    <tr>
                      <th>日期</th>
                      <th>类目</th>
                      <th>浏览</th>
                      <th>购买</th>
                      <th>成交额</th>
                      <th>转化率</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCategories.slice(0, 12).map((row) => (
                      <tr key={`${row.dt}-${row.category_level1}`}>
                        <td>{row.dt}</td>
                        <td>{row.category_level1}</td>
                        <td>{number(row.views)}</td>
                        <td>{number(row.purchases)}</td>
                        <td>{money(row.revenue)}</td>
                        <td>{percent(row.conversion_rate)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <table aria-label="用户粒度代表样本">
                  <thead>
                    <tr>
                      <th>日期</th>
                      <th>用户</th>
                      <th>偏好类目</th>
                      <th>会话</th>
                      <th>浏览</th>
                      <th>购买</th>
                      <th>成交额</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredUsers.slice(0, 12).map((row) => (
                      <tr key={`${row.dt}-${row.user_id}`}>
                        <td>{row.dt}</td>
                        <td>{row.user_id}</td>
                        <td>{row.preferred_category_level1 ?? '未知'}</td>
                        <td>{number(row.sessions)}</td>
                        <td>{number(row.views)}</td>
                        <td>{number(row.purchases)}</td>
                        <td>{money(row.revenue)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {selectedRows.length === 0 ? <p className="empty-copy">{viewCopy[selectedView].empty}</p> : null}
            </div>
          </article>

          <article className="feature-preview-panel">
            <div className="panel-title compact">
              <div>
                <h2>字段字典联动</h2>
                <p>只显示当前粒度相关字段，避免老师把字段表和样本表混在一起。</p>
              </div>
              <Boxes size={19} />
            </div>
            <div className="feature-dictionary-grid feature-dictionary-scroll">
              {selectedFeatures.map((feature) => (
                <div className="feature-dictionary-item" key={feature.feature_name}>
                  <strong>{feature.chinese_name}</strong>
                  <span>{grainLabel(feature.grain)} · {label('frequency', feature.refresh_frequency)}</span>
                  <small>{feature.source}</small>
                </div>
              ))}
              {selectedFeatures.length === 0 ? <p className="empty-copy">当前粒度暂无独立字段字典，使用通用质量与血缘证据。</p> : null}
            </div>
          </article>
        </div>
      </section>

      <section className="feature-evidence-section" aria-label="特征集市底层证据图">
        <div className="feature-evidence-head">
          <div>
            <span className="eyebrow">Evidence Graphs</span>
            <h2>底层数据图回答 4 个问题</h2>
            <p>先看能不能用，再看质量是否过线，最后追溯字段定义和产物流向。</p>
          </div>
          <div className="feature-evidence-mini">
            <span>
              <strong>{number(totalFeatureCount)}</strong>
              特征字段
            </span>
            <span>
              <strong>{number(readinessCheckRows.length)}</strong>
              质量检查
            </span>
            <span>
              <strong>{number(lineageRows.length)}</strong>
              血缘边
            </span>
          </div>
        </div>

        <div className="feature-evidence-grid">
          <ChartPanel
            title="1. 特征就绪结构"
            subtitle="回答：可用字段分别落在哪些业务粒度，而不是只看一个全局 100%。"
            option={featureReadinessOption(readinessChartRows)}
            isEmpty={!readinessChartRows.length}
            annotations={[
              { label: '就绪字段', value: `${number(readyFeatureCount)} / ${number(totalFeatureCount)}`, tone: 'success' },
              { label: '粒度分组', value: number(readinessChartRows.length), tone: 'info' },
            ]}
            summary={`当前 ${number(readyFeatureCount)} / ${number(totalFeatureCount)} 个字段已就绪；圆环按商品、类目、用户和运行审计粒度拆分字段数量。`}
          />
          <ChartPanel
            title="2. 质量健康度矩阵"
            subtitle="回答：即使门禁都通过，各维度距离满分还有多少差异。"
            option={featureQualityOption(readinessCheckRows)}
            isEmpty={!readinessCheckRows.length}
            annotations={[
              { label: '最低健康度', value: `${(lowestQualityScore * 100).toFixed(1)}%`, tone: lowestQualityScore >= 0.9 ? 'success' : lowestQualityScore >= 0.6 ? 'warning' : 'danger' },
              { label: '失败项', value: number(failedCheckCount), tone: failedCheckCount ? 'danger' : 'success' },
            ]}
            summary={
              readiness.data
                ? `集市状态为 ${statusLabel(readiness.data.status)}；条长由字段就绪率、分区覆盖率、迟到控制、新鲜度余量和隔离控制的真实比例计算。`
                : '等待就绪度评估。'
            }
          />
          <article className="data-panel ops-card feature-dictionary-panel">
            <div className="panel-title">
              <div>
                <h2>3. 特征字典</h2>
                <p>回答：每个字段是什么、按什么粒度刷新、有哪些质量断言。</p>
              </div>
              <Boxes size={20} />
            </div>
            <div className="feature-dictionary-summary">
              <span>
                <strong>{number(featureRows.length)}</strong>
                字段
              </span>
              <span>
                <strong>{number(featureGrainCount)}</strong>
                粒度
              </span>
              <span>
                <strong>{number(selectedFeatures.length)}</strong>
                当前层相关
              </span>
            </div>
            <div className="feature-dictionary-grid feature-dictionary-scroll">
              {featureRows.map((feature) => (
                <div className="feature-dictionary-item" key={feature.feature_name}>
                  <strong>{feature.chinese_name}</strong>
                  <span>{grainLabel(feature.grain)} · {label('frequency', feature.refresh_frequency)}</span>
                  <small>{feature.quality_assertions.map((item) => fieldLabel(item)).join('、')}</small>
                </div>
              ))}
              {featureRows.length === 0 ? <p className="empty-copy">等待特征字典。</p> : null}
            </div>
          </article>
          <div className="feature-lineage-panel">
            <ChartPanel
              title="4. 特征血缘图"
              subtitle="回答：原始行为日志如何加工成下游算法可用的特征产物。"
              chartId="feature-mart-lineage-dag"
              option={featureLineageOption(lineageRows)}
              isEmpty={!lineageRows.length}
              annotations={[
                { label: '节点可拖动', value: '可交互', tone: 'info' },
                { label: '依赖边', value: number(lineageRows.length), tone: 'success' },
              ]}
              actionHint="拖动节点或滚轮缩放，可查看原始日志到算法产物的路径。"
              summary={lineageRows.length ? `当前血缘图覆盖 ${lineageRows.length} 条产物依赖边；节点大小和颜色表示产物层级。` : '等待血缘数据。'}
            />
          </div>
        </div>
      </section>

      <section className="ops-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>质量审计</h2>
              <p>稳定事件键、隔离率和源数据坏行统计。</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <div className="quality-checks">
            {(quality.data?.checks ?? []).map((check) => (
              <div className={`quality-check tone-${check.passed ? 'success' : 'danger'}`} key={check.name}>
                <span>{fieldLabel(check.name)}</span>
                <strong>
                  {check.actual} {check.operator} {check.expected}
                </strong>
              </div>
            ))}
          </div>
          <dl>
            <dt>重复事件键</dt>
            <dd>{number(quality.data?.duplicate_event_keys)}</dd>
            <dt>隔离行数</dt>
            <dd>{number(quality.data?.quarantined_rows)}</dd>
            <dt>非法事件</dt>
            <dd>{number(quality.data?.invalid_event_type_rows)}</dd>
          </dl>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>分区与水位</h2>
              <p>按 dt 输出的日级事实层覆盖情况。</p>
            </div>
            <GitBranch size={20} />
          </div>
          <dl>
            <dt>最早分区</dt>
            <dd>{partitions.data?.min_dt ?? '待生成'}</dd>
            <dt>最新分区</dt>
            <dd>{partitions.data?.max_dt ?? '待生成'}</dd>
            <dt>水位时间</dt>
            <dd>{freshness.data?.watermark_time ?? '待生成'}</dd>
            <dt>缺失分区</dt>
            <dd>{partitions.data?.missing.length ? partitions.data.missing.join(', ') : '无'}</dd>
          </dl>
          <div className="partition-strip" aria-label="特征集市分区">
            {(partitions.data?.partitions ?? []).slice(0, 32).map((partition) => (
              <span
                aria-label={`${partition.dt}，${statusLabel(partition.status)}，${number(partition.rows)} 行`}
                className={`partition-cell tone-${partition.status}`}
                key={partition.dt}
                title={`${partition.dt}: ${partition.rows}`}
              >
                {partition.dt.slice(5)}
              </span>
            ))}
          </div>
        </article>
      </section>

      <details className="detail-table-disclosure">
        <summary>查看商品特征预览</summary>
        <section className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>商品特征预览</h2>
              <p>日级商品行为表，用于推荐、优化和异常检测复用。</p>
            </div>
            <Boxes size={20} />
          </div>
          <div className="table-scroll">
            <table aria-label="商品特征预览">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>商品</th>
                  <th>品牌</th>
                  <th>类目</th>
                  <th>浏览</th>
                  <th>加购</th>
                  <th>购买</th>
                  <th>成交额</th>
                  <th>购买转化</th>
                </tr>
              </thead>
              <tbody>
                {(products.data ?? []).map((row) => (
                  <tr key={`${row.dt}-${row.product_id}`}>
                    <td>{row.dt}</td>
                    <td>{row.product_id}</td>
                    <td>{row.brand}</td>
                    <td>{row.category_level1}</td>
                    <td>{number(row.views)}</td>
                    <td>{number(row.carts)}</td>
                    <td>{number(row.purchases)}</td>
                    <td>{money(row.revenue)}</td>
                    <td>{percent(row.view_to_purchase_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </details>

      <details className="detail-table-disclosure">
        <summary>查看类目与用户特征预览</summary>
        <section className="ops-grid">
          <article className="data-panel jobs-panel">
            <div className="panel-title">
              <div>
                <h2>类目特征</h2>
                <p>日级类目行为聚合结果。</p>
              </div>
              <Clock3 size={20} />
            </div>
            <div className="table-scroll">
              <table aria-label="类目特征预览">
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>类目</th>
                    <th>浏览</th>
                    <th>购买</th>
                    <th>成交额</th>
                    <th>转化率</th>
                  </tr>
                </thead>
                <tbody>
                  {(categories.data ?? []).map((row) => (
                    <tr key={`${row.dt}-${row.category_level1}`}>
                      <td>{row.dt}</td>
                      <td>{row.category_level1}</td>
                      <td>{number(row.views)}</td>
                      <td>{number(row.purchases)}</td>
                      <td>{money(row.revenue)}</td>
                      <td>{percent(row.conversion_rate)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>

          <article className="data-panel jobs-panel">
            <div className="panel-title">
              <div>
                <h2>用户特征</h2>
                <p>日级用户行为聚合结果。</p>
              </div>
              <Clock3 size={20} />
            </div>
            <div className="table-scroll">
              <table aria-label="用户特征预览">
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>用户</th>
                    <th>会话</th>
                    <th>浏览</th>
                    <th>购买</th>
                    <th>成交额</th>
                    <th>偏好类目</th>
                  </tr>
                </thead>
                <tbody>
                  {(users.data ?? []).map((row) => (
                    <tr key={`${row.dt}-${row.user_id}`}>
                      <td>{row.dt}</td>
                      <td>{row.user_id}</td>
                      <td>{number(row.sessions)}</td>
                      <td>{number(row.views)}</td>
                      <td>{number(row.purchases)}</td>
                      <td>{money(row.revenue)}</td>
                      <td>{row.preferred_category_level1 ?? '未知'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>
        </section>
      </details>
    </>
  );
}
