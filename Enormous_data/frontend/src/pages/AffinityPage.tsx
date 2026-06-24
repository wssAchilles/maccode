import { Focus, GitBranch, Layers, MousePointer2, Network, PackageSearch, Search, ShieldCheck, SlidersHorizontal } from 'lucide-react';
import { useMemo, useState } from 'react';
import {
  useAffinityCentrality,
  useAffinityCommunities,
  useAffinityEdges,
  useAffinityNodes,
  useAffinityOpportunities,
  useAffinityQuality,
  useAffinitySummary,
} from '../api/hooks';
import { AlgorithmEvidenceBand, type AlgorithmEvidenceTone } from '../components/AlgorithmEvidenceBand';
import { ChartPanel, type DashboardChartOption } from '../components/ChartPanel';
import { algorithmCopy, displayValue, fieldLabel, label, listLabels, statusLabel } from '../i18n/displayText';
import { donutOption, horizontalBarOption } from '../lib/chartOptions';
import type { AffinityCentrality, AffinityEdge, AffinityNode, NamedValue } from '../types/api';

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
  return typeof value === 'number' ? value.toFixed(3) : '待生成';
}

function statusTone(status?: string) {
  if (status === 'passed' || status === 'low') return 'success';
  if (status === 'needs_review' || status === 'medium') return 'warning';
  return 'danger';
}

function evidenceTone(status?: string, sparseGraph?: boolean): AlgorithmEvidenceTone {
  if (sparseGraph) return 'warning';
  return statusTone(status) as AlgorithmEvidenceTone;
}

function relationLabel(relation: string) {
  return label('relation', relation);
}

function relationTone(relation?: string) {
  if (relation === 'co_purchase') return '购买闭环';
  if (relation === 'co_cart') return '加购意图';
  if (relation === 'co_view') return '浏览共现';
  return '全部关系';
}

function opportunityLabel(type?: string) {
  if (type === 'bundle') return '组合搭配';
  if (type === 'cross_sell') return '交叉销售';
  if (type === 'substitute') return '替代推荐';
  if (type === 'category_bridge') return '跨品类桥接';
  return '全部机会';
}

function opportunityMeta(type?: string) {
  if (type === 'bundle') {
    return {
      relationType: 'co_purchase',
      purpose: '把经常一起购买的商品放进套装、搭配购或详情页组合位。',
      evidence: '主要看共同购买、提升度和支持度。',
      empty: '当前没有达到阈值的共同购买组合。',
    };
  }
  if (type === 'cross_sell') {
    return {
      relationType: 'co_cart',
      purpose: '在购物车、结算页或推荐位补充关联商品，提升连带购买。',
      evidence: '主要看共同加购和同类商品的补购关系。',
      empty: '当前没有达到阈值的交叉销售机会。',
    };
  }
  if (type === 'substitute') {
    return {
      relationType: 'co_view',
      purpose: '给用户准备同类替代商品，避免缺货、价格不合适时直接流失。',
      evidence: '主要看共同浏览、同类不同品牌和相似兴趣。',
      empty: '当前没有达到阈值的替代推荐机会。',
    };
  }
  if (type === 'category_bridge') {
    return {
      relationType: '',
      purpose: '发现跨品类跳转关系，用于频道页、主题活动或跨类目推荐。',
      evidence: '主要看不同品类之间的高提升度关系。',
      empty: '当前没有达到阈值的跨品类桥接机会。',
    };
  }
  return {
    relationType: '',
    purpose: '展示全部可运营机会，用于先判断哪类动作最值得复核。',
    evidence: '综合共同浏览、共同加购、共同购买和跨品类关系。',
    empty: '当前没有达到阈值的机会。',
  };
}

function productLabel(entityId?: string | null, rawLabel?: string | null) {
  if (entityId) return `商品 ${entityId}`;
  if (rawLabel) return rawLabel.replace(/^product\s+/i, '商品 ');
  return '商品';
}

function edgeTitle(edge?: AffinityEdge | null) {
  if (!edge) return '等待关系边';
  return `${productLabel(edge.source_id, edge.source_label)} 至 ${productLabel(edge.target_id, edge.target_label)}`;
}

function communityLabel(communityId?: string | null, category?: string | null) {
  const rawCategory = category || communityId?.replace(/^category:/, '');
  return rawCategory ? `${displayValue(rawCategory)} 社区` : '未分社区';
}

function escapeTooltip(value: unknown) {
  return String(value ?? '暂无').replace(/[&<>"']/g, (char) => {
    const replacements: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    };
    return replacements[char] ?? char;
  });
}

function centralityRows(rows: AffinityCentrality[]): NamedValue[] {
  return rows.map((row) => ({ name: `${row.brand} ${row.entity_id}`, value: Number((row.centrality_score * 100).toFixed(1)) }));
}

function relationRows(edges: AffinityEdge[]): NamedValue[] {
  const counts = new Map<string, number>();
  edges.forEach((edge) => counts.set(edge.relation_type, (counts.get(edge.relation_type) ?? 0) + edge.support));
  return Array.from(counts.entries()).map(([name, value]) => ({ name, value }));
}

const graphPalette = ['#5eead4', '#60a5fa', '#fbbf24', '#c084fc', '#fb7185', '#34d399', '#f97316', '#a3e635'];

function relationColor(relationType?: string) {
  if (relationType === 'co_purchase') return 'rgba(251, 191, 36, 0.72)';
  if (relationType === 'co_cart') return 'rgba(96, 165, 250, 0.62)';
  if (relationType === 'co_view') return 'rgba(94, 234, 212, 0.48)';
  return 'rgba(148, 163, 184, 0.38)';
}

type AffinityGraphNode = {
  id: string;
  name: string;
  brand: string;
  categoryName: string;
  communityName: string;
  centralityScore: number;
  degree: number;
  revenue: number;
  symbolSize: number;
  category: number;
  value: number;
  itemStyle?: {
    color?: string;
    opacity?: number;
    borderColor?: string;
    borderWidth?: number;
    shadowBlur?: number;
    shadowColor?: string;
  };
};

type AffinityGraphLink = {
  source: string;
  target: string;
  value: number;
  relationType: string;
  support: number;
  confidence: number;
  lift: number;
  lineStyle: { color: string; width: number; opacity: number };
};

function buildAffinityGraphOption(
  nodeRows: AffinityNode[],
  edgeRows: AffinityEdge[],
  centralityRowsData: AffinityCentrality[],
  selectedEntity: string,
  options: { selectedCommunityId?: string; showLabels?: boolean } = {},
): { option: DashboardChartOption; nodes: AffinityGraphNode[]; edgeCount: number; topNode?: AffinityGraphNode } {
  const categoryIndexes = new Map<string, number>();
  const categories: Array<{ name: string; itemStyle: { color: string } }> = [];
  const centralityLookup = new Map(centralityRowsData.map((row) => [row.entity_id, row]));
  const nodeLookup = new Map<string, AffinityGraphNode>();

  const categoryIndex = (communityNameValue: string) => {
    const existing = categoryIndexes.get(communityNameValue);
    if (existing !== undefined) return existing;
    const next = categories.length;
    categoryIndexes.set(communityNameValue, next);
    categories.push({ name: communityNameValue, itemStyle: { color: graphPalette[next % graphPalette.length] } });
    return next;
  };

  const upsertNode = (input: {
    entityId: string;
    brand?: string | null;
    category?: string | null;
    communityId?: string | null;
    centralityScore?: number | null;
    degree?: number | null;
    revenue?: number | null;
  }) => {
    if (!input.entityId) return;
    const centrality = centralityLookup.get(input.entityId);
    const current = nodeLookup.get(input.entityId);
    const brand = input.brand || centrality?.brand || current?.brand || '未知品牌';
    const categoryName = displayValue(input.category || centrality?.category_level1 || current?.categoryName || 'unknown');
    const communityNameValue = communityLabel(input.communityId || centrality?.community_id, input.category || centrality?.category_level1);
    const centralityScore = Math.max(current?.centralityScore ?? 0, Number(input.centralityScore ?? centrality?.centrality_score ?? 0));
    const degree = Math.max(current?.degree ?? 0, Number(input.degree ?? centrality?.degree ?? 0));
    const revenue = Math.max(current?.revenue ?? 0, Number(input.revenue ?? centrality?.revenue ?? 0));
    const category = categoryIndex(communityNameValue);
    const isSelected = selectedEntity && selectedEntity === input.entityId;
    const symbolSize = Math.max(22, Math.min(62, 22 + centralityScore * 30 + Math.log1p(Math.max(degree, 0)) * 5.5));
    const fillColor = graphPalette[category % graphPalette.length];
    nodeLookup.set(input.entityId, {
      id: input.entityId,
      name: `${brand} ${input.entityId}`,
      brand,
      categoryName,
      communityName: communityNameValue,
      centralityScore,
      degree,
      revenue,
      symbolSize,
      category,
      value: Number((centralityScore * 100).toFixed(1)),
      itemStyle: {
        color: fillColor,
        opacity: isSelected ? 1 : 0.88,
        borderColor: isSelected ? '#fbbf24' : 'rgba(226, 232, 240, 0.22)',
        borderWidth: isSelected ? 5 : 1,
        shadowBlur: isSelected ? 28 : 11,
        shadowColor: isSelected ? 'rgba(251, 191, 36, 0.58)' : `${fillColor}55`,
      },
    });
  };

  nodeRows.forEach((node) =>
    upsertNode({
      entityId: node.entity_id,
      brand: node.brand,
      category: node.category_level1,
      communityId: node.community_id,
      degree: node.degree,
      revenue: node.revenue,
    }),
  );
  centralityRowsData.forEach((node) =>
    upsertNode({
      entityId: node.entity_id,
      brand: node.brand,
      category: node.category_level1,
      communityId: node.community_id,
      centralityScore: node.centrality_score,
      degree: node.degree,
      revenue: node.revenue,
    }),
  );
  edgeRows.forEach((edge) => {
    upsertNode({ entityId: edge.source_id, brand: edge.source_brand, category: edge.source_category });
    upsertNode({ entityId: edge.target_id, brand: edge.target_brand, category: edge.target_category });
  });

  const visibleNodes = Array.from(nodeLookup.values())
    .filter((node) => !options.selectedCommunityId || node.communityName === communityLabel(options.selectedCommunityId))
    .sort((left, right) => {
      if (left.id === selectedEntity) return -1;
      if (right.id === selectedEntity) return 1;
      return right.centralityScore - left.centralityScore || right.degree - left.degree || right.revenue - left.revenue;
    })
    .slice(0, 42);
  const visibleIds = new Set(visibleNodes.map((node) => node.id));
  const links: AffinityGraphLink[] = edgeRows
    .filter((edge) => visibleIds.has(edge.source_id) && visibleIds.has(edge.target_id))
    .slice(0, 96)
    .map((edge) => ({
      source: edge.source_id,
      target: edge.target_id,
      value: edge.support,
      relationType: edge.relation_type,
      support: edge.support,
      confidence: edge.confidence,
      lift: edge.lift,
      lineStyle: {
        color: relationColor(edge.relation_type),
        width: Math.max(0.9, Math.min(5.5, 0.9 + edge.support / 10 + edge.lift / 2.4)),
        opacity: Math.max(0.22, Math.min(0.76, 0.22 + edge.confidence)),
      },
    }));

  const option: DashboardChartOption = {
    color: graphPalette,
    legend: {
      top: 0,
      type: 'scroll',
      data: categories.map((item) => item.name),
      textStyle: { color: '#9ca3af' },
    },
    tooltip: {
      trigger: 'item',
      formatter: (rawParams) => {
        const params = Array.isArray(rawParams) ? rawParams[0] : rawParams;
        const item = params as { data?: unknown; dataType?: string } | undefined;
        const data = item?.data as Partial<AffinityGraphNode & AffinityGraphLink>;
        if (item?.dataType === 'edge') {
          return [
            `<strong>${escapeTooltip(productLabel(String(data.source || '')))} -> ${escapeTooltip(productLabel(String(data.target || '')))}</strong>`,
            `关系：${escapeTooltip(relationLabel(String(data.relationType || '')))}`,
            `支持度：${escapeTooltip(data.support)}`,
            `置信度：${escapeTooltip(percent(Number(data.confidence || 0)))}`,
            `提升度：${escapeTooltip(score(Number(data.lift || 0)))}`,
          ].join('<br/>');
        }
        return [
          `<strong>${escapeTooltip(data.name)}</strong>`,
          `社区：${escapeTooltip(data.communityName)}`,
          `品类：${escapeTooltip(data.categoryName)}`,
          `中心性：${escapeTooltip(score(Number(data.centralityScore || 0)))}`,
          `度数：${escapeTooltip(data.degree)}`,
          `收入：${escapeTooltip(money(Number(data.revenue || 0)))}`,
        ].join('<br/>');
      },
    },
    aria: {
      enabled: true,
      description: `商品关系力导向图，展示 ${visibleNodes.length} 个商品节点和 ${links.length} 条关系边，节点越大代表中心性越高，连线越粗代表支持度和提升度越高。`,
    },
    series: [
      {
        name: '商品关系',
        type: 'graph',
        layout: 'force',
        data: visibleNodes,
        links,
        categories,
        roam: true,
        draggable: true,
        nodeScaleRatio: 0.45,
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 6],
        label: {
          show: options.showLabels ?? false,
          position: 'right',
          formatter: '{b}',
          color: 'rgba(226, 232, 240, 0.84)',
          fontSize: 10,
          width: 108,
          overflow: 'truncate',
        },
        edgeLabel: {
          show: false,
          formatter: (params) => relationLabel(String((params.data as Partial<AffinityGraphLink>).relationType || '')),
        },
        lineStyle: {
          curveness: 0.16,
        },
        emphasis: {
          focus: 'adjacency',
          label: {
            show: true,
            color: '#f8fafc',
            fontWeight: 800,
          },
          lineStyle: {
            width: 5,
            opacity: 0.9,
          },
        },
        force: {
          repulsion: 250,
          edgeLength: [88, 190],
          gravity: 0.06,
        },
        animationDurationUpdate: 700,
      },
    ],
  };

  return { option, nodes: visibleNodes, edgeCount: links.length, topNode: visibleNodes[0] };
}

export function AffinityPage() {
  const [query, setQuery] = useState('');
  const [selectedEntity, setSelectedEntity] = useState('');
  const [relationType, setRelationType] = useState('');
  const [opportunityType, setOpportunityType] = useState('');
  const [selectedCommunityId, setSelectedCommunityId] = useState('');
  const [edgeLiftThreshold, setEdgeLiftThreshold] = useState(0);
  const [showLabels, setShowLabels] = useState(false);
  const summary = useAffinitySummary();
  const nodes = useAffinityNodes({ entity_type: 'product', q: query || undefined, limit: 80 });
  const edges = useAffinityEdges({ entity_id: selectedEntity || undefined, relation_type: relationType || undefined, limit: 120 });
  const communities = useAffinityCommunities(40);
  const opportunities = useAffinityOpportunities({ type: opportunityType || undefined, confidence: 0.05, limit: 120 });
  const allOpportunities = useAffinityOpportunities({ confidence: 0.05, limit: 120 });
  const centrality = useAffinityCentrality({ limit: 40 });
  const quality = useAffinityQuality();
  const hasError = summary.isError || nodes.isError || edges.isError || communities.isError || opportunities.isError || allOpportunities.isError || quality.isError;
  const optionalMissing = centrality.isError;
  const strongest = summary.data?.strongest_edge ?? edges.data?.[0] ?? null;
  const selectedNode = useMemo(
    () => nodes.data?.find((node) => node.entity_id === selectedEntity) ?? nodes.data?.[0],
    [nodes.data, selectedEntity],
  );
  const centralityData = centrality.data ?? [];
  const edgeRows = useMemo(
    () => (edges.data ?? []).filter((edge) => edge.lift >= edgeLiftThreshold),
    [edges.data, edgeLiftThreshold],
  );
  const communityRows: NamedValue[] = (communities.data ?? []).map((row) => ({ name: row.category_level1, value: row.edge_count }));
  const topCentrality = centralityData[0];
  const relationMix = relationRows(edgeRows);
  const opportunityRows = opportunities.data ?? [];
  const allOpportunityRows = allOpportunities.data ?? [];
  const opportunityCounts = useMemo(() => {
    const counts = new Map<string, number>();
    allOpportunityRows.forEach((row) => counts.set(row.type, (counts.get(row.type) ?? 0) + 1));
    return counts;
  }, [allOpportunityRows]);
  const activeOpportunityMeta = opportunityMeta(opportunityType);
  const topOpportunity = opportunityRows[0] ?? summary.data?.top_opportunity ?? null;
  const handleOpportunityChange = (nextType: string) => {
    setOpportunityType(nextType);
    setRelationType(opportunityMeta(nextType).relationType);
  };
  const graphEvidence = useMemo(
    () => buildAffinityGraphOption(nodes.data ?? [], edgeRows, centralityData, selectedEntity, { selectedCommunityId, showLabels }),
    [nodes.data, edgeRows, centralityData, selectedEntity, selectedCommunityId, showLabels],
  );
  const graphTone = evidenceTone(summary.data?.quality_status, summary.data?.sparse_graph);
  const selectedCentrality = centralityData.find((node) => node.entity_id === selectedNode?.entity_id);
  const selectedCommunity = communities.data?.find((community) => community.community_id === (selectedCommunityId || selectedNode?.community_id));
  const selectedConnections = edgeRows
    .filter((edge) => edge.source_id === selectedNode?.entity_id || edge.target_id === selectedNode?.entity_id)
    .slice(0, 5);
  const graphCoverage = summary.data?.node_count
    ? Math.min(1, graphEvidence.nodes.length / Math.max(summary.data.node_count, 1))
    : 0;
  const activeRelationCopy = relationType
    ? `${relationLabel(relationType)}：只看 ${relationTone(relationType)} 的关系边。`
    : '全部关系：共同浏览、共同加购和共同购买同时参与图谱。';
  const graphReadHint = selectedNode
    ? `${selectedNode.brand} ${selectedNode.entity_id} 位于 ${communityLabel(selectedNode.community_id, selectedNode.category_level1)}，度数 ${number(selectedNode.degree)}，收入 ${money(selectedNode.revenue)}。`
    : '先点击图中的节点或左侧候选商品，右侧会解释这个节点为什么重要。';

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">商品关系图谱</span>
        <h1>商品关系图谱与搭配洞察</h1>
        <p>用共同浏览、共同加购、共同购买构建商品关系证据，优先展示中心性、社群和机会强度。</p>
      </section>

      {hasError ? <div className="error-banner">商品关系图谱缓存尚未生成，请先运行 Spark 刷新任务。</div> : null}
      {optionalMissing ? <div className="error-banner">中心性产物尚未生成，已保留基础图谱视图。</div> : null}
      {summary.data?.sparse_graph ? (
        <div className="error-banner">当前图谱样本稀疏，仅保留低置信关系证据，不建议直接上线搭配或替代策略。</div>
      ) : null}

      <AlgorithmEvidenceBand
        title="图谱证据结论"
        status={summary.data?.sparse_graph ? '需复核' : statusLabel(summary.data?.quality_status)}
        tone={graphTone}
        description={algorithmCopy(summary.data?.recommended_action ?? '等待商品关系图谱产物')}
        caveat="当前中心性用于离线运营复核；真实社区算法和线上策略效果仍需单独评估。"
        icon={<Network size={22} />}
        metrics={[
          {
            label: '中心商品',
            value: topCentrality ? `${topCentrality.brand} ${topCentrality.entity_id}` : '待生成',
            detail: topCentrality ? `得分 ${score(topCentrality.centrality_score)}` : '等待中心性产物',
          },
          {
            label: '社区数量',
            value: number(summary.data?.community_count),
            detail: `${number(summary.data?.edge_count)} 条关系边`,
          },
          {
            label: '稀疏风险',
            value: summary.data?.sparse_graph ? '是' : '否',
            detail: `有效会话 ${number(summary.data?.eligible_session_count)}`,
          },
        ]}
      />

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>图谱边</span>
          <strong>{number(summary.data?.edge_count)}</strong>
          <small>{number(summary.data?.node_count)} 个商品节点</small>
        </article>
        <article className="metric-card">
          <span>机会队列</span>
          <strong>{number(summary.data?.opportunity_count)}</strong>
          <small>{number(summary.data?.community_count)} 个商品社区</small>
        </article>
        <article className="metric-card tone-warning">
          <span>有效会话</span>
          <strong>{number(summary.data?.eligible_session_count)}</strong>
          <small>最小支持度 {number(summary.data?.min_support)}</small>
        </article>
        <article className="metric-card">
          <span>最强提升度</span>
          <strong>{score(strongest?.lift)}</strong>
          <small>{strongest ? relationLabel(strongest.relation_type) : '待生成'}</small>
        </article>
      </section>

      <section className="affinity-workbench" aria-label="商品关系图谱探索工作台">
        <div className="affinity-workbench-head">
          <div>
            <span className="eyebrow">Obsidian 式局部邻域探索</span>
            <h2>先聚焦一个商品，再观察它的关系强度和社区位置</h2>
            <p>{activeRelationCopy} {graphReadHint}</p>
          </div>
          <div className="affinity-workbench-kpis" aria-label="当前图谱视口指标">
            <div>
              <span>当前画布</span>
              <strong>{number(graphEvidence.nodes.length)} / {number(summary.data?.node_count)}</strong>
              <small>节点覆盖 {percent(graphCoverage)}</small>
            </div>
            <div>
              <span>关系边</span>
              <strong>{number(graphEvidence.edgeCount)}</strong>
              <small>提升度阈值 ≥ {edgeLiftThreshold.toFixed(1)}</small>
            </div>
            <div>
              <span>选中商品</span>
              <strong>{selectedNode ? selectedNode.entity_id : '未聚焦'}</strong>
              <small>{selectedNode ? selectedNode.brand : '点击节点开始'}</small>
            </div>
          </div>
        </div>

        <div className="affinity-graph-shell">
          <aside className="affinity-graph-controls" aria-label="商品图谱控制台">
            <div className="affinity-control-title">
              <SlidersHorizontal size={18} />
              <div>
                <h3>图谱控制</h3>
                <p>控制画布显示范围，不改后端训练结果。</p>
              </div>
            </div>
            <label htmlFor="affinity-query">
              <span><Search size={15} /> 搜索商品、品牌或类目</span>
              <input
                id="affinity-query"
                name="affinity-query"
                className="text-input"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="输入商品 ID、品牌或类目"
              />
            </label>
            <div className="affinity-control-group">
              <span><GitBranch size={15} /> 关系类型</span>
              <div className="affinity-segmented">
                {[
                  { value: '', label: '全部' },
                  { value: 'co_view', label: '共看' },
                  { value: 'co_cart', label: '加购' },
                  { value: 'co_purchase', label: '购买' },
                ].map((item) => (
                  <button type="button" className={relationType === item.value ? 'is-active' : ''} key={item.value || 'all'} onClick={() => setRelationType(item.value)}>
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
            <label htmlFor="affinity-lift-threshold" className="affinity-range-control">
              <span><Focus size={15} /> 最小提升度</span>
              <strong>{edgeLiftThreshold.toFixed(1)}</strong>
              <input
                id="affinity-lift-threshold"
                min="0"
                max="5"
                step="0.1"
                type="range"
                value={edgeLiftThreshold}
                onChange={(event) => setEdgeLiftThreshold(Number(event.target.value))}
              />
            </label>
            <div className="affinity-control-group">
              <span><Layers size={15} /> 社区聚焦</span>
              <div className="affinity-community-list">
                <button type="button" className={!selectedCommunityId ? 'is-active' : ''} onClick={() => setSelectedCommunityId('')}>
                  <strong>全部社区</strong>
                  <small>{number(summary.data?.community_count)} 个社区</small>
                </button>
                {(communities.data ?? []).slice(0, 6).map((community) => (
                  <button
                    type="button"
                    className={selectedCommunityId === community.community_id ? 'is-active' : ''}
                    key={community.community_id}
                    onClick={() => setSelectedCommunityId(community.community_id)}
                  >
                    <strong>{communityLabel(community.community_id, community.category_level1)}</strong>
                    <small>{number(community.node_count)} 节点 · {number(community.edge_count)} 边</small>
                  </button>
                ))}
              </div>
            </div>
            <label className="affinity-toggle-row">
              <input type="checkbox" checked={showLabels} onChange={(event) => setShowLabels(event.target.checked)} />
              <span>显示所有节点标签</span>
            </label>
          </aside>

          <div className="affinity-graph-canvas">
            <div className="affinity-canvas-topbar">
              <div>
              <span>Force-directed Graph · {showLabels ? '全标签模式' : '聚焦标签模式'}</span>
                <strong>{selectedCommunity ? communityLabel(selectedCommunity.community_id, selectedCommunity.category_level1) : '全局商品关系'}</strong>
              </div>
              <div className="affinity-legend">
                <span><i className="tone-node" />节点色 = 商品社区</span>
                <span><i className="tone-edge" />线色 = 关系类型</span>
                <span><i className="tone-alert" />金色描边 = 当前聚焦</span>
              </div>
            </div>
            <ChartPanel
              title="商品关系力导向图"
              subtitle="拖动画布、滚轮缩放、点击节点聚焦邻域；节点越大代表中心性越高。"
              chartId="affinity-force-graph"
              option={graphEvidence.option}
              isLoading={nodes.isLoading || edges.isLoading}
              isEmpty={!graphEvidence.nodes.length || !graphEvidence.edgeCount}
              error={
                nodes.error instanceof Error
                  ? nodes.error
                  : edges.error instanceof Error
                    ? edges.error
                    : null
              }
              filterNotice={
                selectedEntity
                  ? `已聚焦 ${selectedNode ? `${selectedNode.brand} ${selectedNode.entity_id}` : productLabel(selectedEntity)}，只显示它的局部邻域关系。`
                  : '点击节点或左侧商品按钮聚焦局部邻域。'
              }
              summary={
                graphEvidence.topNode
                  ? `${graphEvidence.topNode.name} 是当前主节点，画布展示 ${graphEvidence.edgeCount} 条关系边。`
                  : '等待图谱关系数据。'
              }
              onChartClick={(params) => {
                const data = params.data as Partial<AffinityGraphNode>;
                if (params.dataType === 'node' && data.id) {
                  setSelectedEntity(String(data.id));
                }
              }}
            />
            <div className="affinity-node-strip" aria-label="快速聚焦商品">
              <button type="button" className={!selectedEntity ? 'is-active' : ''} onClick={() => setSelectedEntity('')}>
                全部商品
              </button>
              {graphEvidence.nodes.slice(0, 8).map((node) => (
                <button
                  type="button"
                  className={selectedEntity === node.id ? 'is-active' : ''}
                  key={node.id}
                  onClick={() => setSelectedEntity(node.id)}
                >
                  {node.name}
                </button>
              ))}
            </div>
          </div>

          <aside className="affinity-node-inspector" aria-label="选中商品检查器">
            <div className="panel-title">
              <div>
                <h2>实体检查器</h2>
                <p>把节点、边和社区解释成业务含义。</p>
              </div>
              <MousePointer2 size={20} />
            </div>
            <div className="affinity-sku-tile">
              <span>{selectedNode?.category_level1 ?? 'category'}</span>
              <strong>{selectedNode ? `${selectedNode.brand} ${selectedNode.entity_id}` : '选择一个商品'}</strong>
              <small>{selectedNode ? communityLabel(selectedNode.community_id, selectedNode.category_level1) : '点击图中节点查看详情'}</small>
            </div>
            <dl className="affinity-inspector-grid">
              <div>
                <dt>中心性</dt>
                <dd>{score(selectedCentrality?.centrality_score)}</dd>
              </div>
              <div>
                <dt>度数</dt>
                <dd>{number(selectedNode?.degree ?? selectedCentrality?.degree)}</dd>
              </div>
              <div>
                <dt>购买</dt>
                <dd>{number(selectedNode?.purchases ?? selectedCentrality?.purchases)}</dd>
              </div>
              <div>
                <dt>收入</dt>
                <dd>{money(selectedNode?.revenue ?? selectedCentrality?.revenue)}</dd>
              </div>
            </dl>
            <div className="affinity-neighbor-list">
              <h3>最强邻居关系</h3>
              {selectedConnections.length ? selectedConnections.map((edge) => {
                const neighborId = edge.source_id === selectedNode?.entity_id ? edge.target_id : edge.source_id;
                const neighborLabel = edge.source_id === selectedNode?.entity_id ? edge.target_label : edge.source_label;
                return (
                  <button type="button" key={`${edge.source_id}-${edge.target_id}-${edge.relation_type}`} onClick={() => setSelectedEntity(neighborId)}>
                    <span>{productLabel(neighborId, neighborLabel)}</span>
                    <strong>{relationLabel(edge.relation_type)} · lift {score(edge.lift)}</strong>
                    <small>支持度 {number(edge.support)} · 置信度 {percent(edge.confidence)}</small>
                  </button>
                );
              }) : <p>当前商品暂无满足阈值的邻居关系。</p>}
            </div>
            <div className="affinity-inspector-note">
              <strong>怎么读这张图？</strong>
              <p>先看节点大小判断中心商品，再看连线粗细判断搭配证据强弱。点击节点会把画布切换成局部邻域，避免大网过载。</p>
            </div>
          </aside>
        </div>

        <div className="affinity-evidence-dock">
          <article>
            <ShieldCheck size={18} />
            <span>质量门禁</span>
            <strong>{quality.data?.passed ? '已通过' : '需复核'}</strong>
            <small>有效会话 {number(quality.data?.eligible_session_count)} / 全部 {number(quality.data?.session_count)}</small>
          </article>
          <article>
            <Network size={18} />
            <span>当前关系</span>
            <strong>{relationTone(relationType)}</strong>
            <small>{graphEvidence.edgeCount} 条边进入画布</small>
          </article>
          <article className="affinity-opportunity-card">
            <PackageSearch size={18} />
            <span>机会类型</span>
            <strong>{opportunityLabel(opportunityType)}</strong>
            <small>{activeOpportunityMeta.purpose}</small>
            <select value={opportunityType} onChange={(event) => handleOpportunityChange(event.target.value)} aria-label="机会类型">
              <option value="">全部机会（{allOpportunityRows.length}）</option>
              <option value="bundle">组合搭配（{opportunityCounts.get('bundle') ?? 0}）</option>
              <option value="cross_sell">交叉销售（{opportunityCounts.get('cross_sell') ?? 0}）</option>
              <option value="substitute">替代推荐（{opportunityCounts.get('substitute') ?? 0}）</option>
              <option value="category_bridge">跨品类桥接（{opportunityCounts.get('category_bridge') ?? 0}）</option>
            </select>
            <div className="affinity-opportunity-brief">
              <span>证据口径</span>
              <strong>{activeOpportunityMeta.evidence}</strong>
              {topOpportunity ? (
                <small>
                  最强机会：{productLabel(topOpportunity.primary_entity, topOpportunity.primary_label)} → {productLabel(topOpportunity.related_entity, topOpportunity.related_label)}
                  · lift {score(topOpportunity.lift)}
                  · {label('action', topOpportunity.action, { fallback: topOpportunity.action })}
                </small>
              ) : (
                <small>{activeOpportunityMeta.empty}</small>
              )}
            </div>
          </article>
          <article>
            <Layers size={18} />
            <span>社区证据</span>
            <strong>{selectedCommunity ? money(selectedCommunity.revenue) : number(summary.data?.community_count)}</strong>
            <small>{selectedCommunity ? `${number(selectedCommunity.node_count)} 节点 · ${number(selectedCommunity.edge_count)} 边` : '可按左侧社区聚焦'}</small>
          </article>
        </div>
      </section>

      <section className="content-grid visual-first-grid">
        <ChartPanel
          title="中心性排行"
          subtitle="综合 PageRank 与加权度数，识别关键商品"
          option={horizontalBarOption(centralityRows(centralityData).slice(0, 10), '中心性得分', '#39d0c8')}
          isLoading={centrality.isLoading}
          isEmpty={!centralityData.length}
          error={centrality.error instanceof Error ? centrality.error : null}
          summary={topCentrality ? `${topCentrality.brand} ${topCentrality.entity_id} 当前中心性最高，得分 ${score(topCentrality.centrality_score)}。` : '等待中心性产物。'}
        />
        <ChartPanel
          title="关系类型结构"
          subtitle="按支持度汇总共同浏览、加购和购买关系"
          option={donutOption(relationMix, '支持度')}
          isLoading={edges.isLoading}
          isEmpty={!relationMix.length}
          summary={relationMix[0] ? `${relationLabel(relationMix[0].name)} 是当前主要关系。` : '等待关系边数据。'}
        />
        <ChartPanel
          title="社区边规模"
          subtitle="用边数量衡量商品社区内部连接强度"
          option={horizontalBarOption(communityRows, '图谱边数量', '#65b8ff')}
          isLoading={communities.isLoading}
          isEmpty={!communityRows.length}
          summary={communities.data?.[0] ? `${communities.data[0].category_level1} 社区边最多，收入池 ${money(communities.data[0].revenue)}。` : '等待社区数据。'}
        />
      </section>

      <details className="detail-table-disclosure">
        <summary>查看商品节点和关系明细</summary>
        <section className="forecast-main-grid">
          <article className="data-panel ops-card">
            <div className="panel-title">
              <div>
                <h2>商品节点</h2>
                <p>选择商品后同步过滤邻居关系边。</p>
              </div>
            </div>
            <div className="affinity-node-list" aria-label="商品节点列表">
              {(nodes.data ?? []).slice(0, 8).map((node) => (
                <button
                  className={`affinity-node ${selectedEntity === node.entity_id ? 'active' : ''}`}
                  type="button"
                  key={node.entity_id}
                  onClick={() => setSelectedEntity(node.entity_id)}
                >
                  <strong>{productLabel(node.entity_id, node.entity_label)}</strong>
                  <span>{node.brand} · {node.category_level1}</span>
                  <small>{money(node.revenue)} · 度数 {number(node.degree)}</small>
                </button>
              ))}
              {nodes.data?.length === 0 ? <p className="empty-copy">当前搜索没有匹配商品。</p> : null}
            </div>
          </article>

          <article className="data-panel jobs-panel">
            <div className="panel-title">
              <div>
                <h2>邻居关系边</h2>
                <p>{edgeTitle(strongest)}，保留支持度、置信度、提升度、相似度和收入重叠。</p>
              </div>
            </div>
            <div className="table-scroll">
              <table aria-label="商品关系边">
                <thead>
                  <tr>
                    <th>源商品</th>
                    <th>目标商品</th>
                    <th>关系</th>
                    <th>支持度</th>
                    <th>置信度</th>
                    <th>提升度</th>
                    <th>相似度</th>
                    <th>收入重叠</th>
                  </tr>
                </thead>
                <tbody>
                  {edgeRows.map((edge) => (
                    <tr key={`${edge.source_id}-${edge.target_id}-${edge.relation_type}`}>
                      <td>{productLabel(edge.source_id, edge.source_label)}</td>
                      <td>{productLabel(edge.target_id, edge.target_label)}</td>
                      <td><span className="event-chip">{relationLabel(edge.relation_type)}</span></td>
                      <td>{number(edge.support)}</td>
                      <td>{percent(edge.confidence)}</td>
                      <td>{score(edge.lift)}</td>
                      <td>{score(edge.jaccard)}</td>
                      <td>{money(edge.revenue_overlap)}</td>
                    </tr>
                  ))}
                  {edgeRows.length === 0 ? (
                    <tr>
                      <td colSpan={8}>当前筛选没有关系边。</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </article>
        </section>
      </details>

      <details className="detail-table-disclosure">
        <summary>查看搭配、替代和社区证据</summary>
        <section className="ops-grid">
          <article className="data-panel jobs-panel">
            <div className="panel-title">
              <div>
                <h2>搭配与替代机会</h2>
                <p>把高提升度关系转成可复核运营动作。</p>
              </div>
              <PackageSearch size={20} />
            </div>
            <div className="table-scroll">
              <table aria-label="搭配与替代机会">
                <thead>
                  <tr>
                    <th>类型</th>
                    <th>主商品</th>
                    <th>关联商品</th>
                    <th>提升度</th>
                    <th>支持度</th>
                    <th>收入池</th>
                    <th>动作</th>
                  </tr>
                </thead>
                <tbody>
                  {opportunityRows.map((row) => (
                    <tr key={row.opportunity_id}>
                      <td><span className={`status-pill tone-${statusTone(row.risk_level)}`}>{label('risk', row.risk_level)}</span></td>
                      <td>{productLabel(row.primary_entity, row.primary_label)}</td>
                      <td>{productLabel(row.related_entity, row.related_label)}</td>
                      <td>{score(row.lift)}</td>
                      <td>{number(row.support)}</td>
                      <td>{money(row.estimated_revenue_pool)}</td>
                      <td>{label('action', row.action, { fallback: row.action })}</td>
                    </tr>
                  ))}
                  {opportunityRows.length === 0 ? (
                    <tr>
                      <td colSpan={7}>{activeOpportunityMeta.empty}</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </article>

          <article className="data-panel ops-card">
            <div className="panel-title">
              <div>
                <h2>社区证据</h2>
                <p>按商品社区汇总节点、边和收入规模。</p>
              </div>
            </div>
            <div className="quality-checks">
              {(communities.data ?? []).slice(0, 6).map((community) => (
                <div className="quality-check tone-success" key={community.community_id}>
                  <span>{community.category_level1}</span>
                  <strong>{number(community.node_count)} 个节点 · {number(community.edge_count)} 条边</strong>
                </div>
              ))}
            </div>
            <dl>
              <dt>当前商品</dt>
              <dd>{selectedNode ? `${selectedNode.entity_id} · ${selectedNode.brand}` : '暂无'}</dd>
              <dt>所属社区</dt>
              <dd>{selectedNode ? communityLabel(selectedNode.community_id, selectedNode.category_level1) : '暂无'}</dd>
              <dt>原因</dt>
              <dd>{listLabels('relation', summary.data?.strongest_edge ? [summary.data.strongest_edge.relation_type] : [])}</dd>
            </dl>
          </article>
        </section>
      </details>
    </>
  );
}
