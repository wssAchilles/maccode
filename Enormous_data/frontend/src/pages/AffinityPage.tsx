import { Network, PackageSearch, ShieldCheck } from 'lucide-react';
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

const graphPalette = ['#39d0c8', '#65b8ff', '#f59e0b', '#a78bfa', '#fb7185', '#34d399', '#f97316'];

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
  itemStyle?: { borderColor?: string; borderWidth?: number };
};

type AffinityGraphLink = {
  source: string;
  target: string;
  value: number;
  relationType: string;
  support: number;
  confidence: number;
  lift: number;
  lineStyle: { width: number; opacity: number };
};

function buildAffinityGraphOption(
  nodeRows: AffinityNode[],
  edgeRows: AffinityEdge[],
  centralityRowsData: AffinityCentrality[],
  selectedEntity: string,
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
    const symbolSize = Math.max(28, Math.min(68, 28 + centralityScore * 28 + Math.log1p(Math.max(degree, 0)) * 6));
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
      category: categoryIndex(communityNameValue),
      value: Number((centralityScore * 100).toFixed(1)),
      itemStyle: selectedEntity && selectedEntity === input.entityId ? { borderColor: '#f59e0b', borderWidth: 4 } : current?.itemStyle,
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
        width: Math.max(1.5, Math.min(7, 1.5 + edge.support / 8 + edge.lift / 2)),
        opacity: Math.max(0.3, Math.min(0.78, 0.28 + edge.confidence)),
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
        edgeSymbolSize: [0, 8],
        label: {
          show: true,
          position: 'right',
          formatter: '{b}',
          color: '#dbe5ee',
          fontSize: 11,
          width: 110,
          overflow: 'truncate',
        },
        edgeLabel: {
          show: false,
          formatter: (params) => relationLabel(String((params.data as Partial<AffinityGraphLink>).relationType || '')),
        },
        lineStyle: {
          color: 'source',
          curveness: 0.12,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 5,
            opacity: 0.9,
          },
        },
        force: {
          repulsion: 180,
          edgeLength: [70, 150],
          gravity: 0.08,
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
  const summary = useAffinitySummary();
  const nodes = useAffinityNodes({ entity_type: 'product', q: query || undefined, limit: 80 });
  const edges = useAffinityEdges({ entity_id: selectedEntity || undefined, relation_type: relationType || undefined, limit: 120 });
  const communities = useAffinityCommunities(40);
  const opportunities = useAffinityOpportunities({ type: opportunityType || undefined, confidence: 0.05, limit: 120 });
  const centrality = useAffinityCentrality({ limit: 40 });
  const quality = useAffinityQuality();
  const hasError = summary.isError || nodes.isError || edges.isError || communities.isError || opportunities.isError || quality.isError;
  const optionalMissing = centrality.isError;
  const strongest = summary.data?.strongest_edge ?? edges.data?.[0] ?? null;
  const selectedNode = useMemo(
    () => nodes.data?.find((node) => node.entity_id === selectedEntity) ?? nodes.data?.[0],
    [nodes.data, selectedEntity],
  );
  const centralityData = centrality.data ?? [];
  const edgeRows = edges.data ?? [];
  const communityRows: NamedValue[] = (communities.data ?? []).map((row) => ({ name: row.category_level1, value: row.edge_count }));
  const topCentrality = centralityData[0];
  const relationMix = relationRows(edgeRows);
  const graphEvidence = useMemo(
    () => buildAffinityGraphOption(nodes.data ?? [], edgeRows, centralityData, selectedEntity),
    [nodes.data, edgeRows, centralityData, selectedEntity],
  );
  const graphTone = evidenceTone(summary.data?.quality_status, summary.data?.sparse_graph);

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

      <section className="toolbar forecast-toolbar" aria-label="商品关系筛选">
        <label htmlFor="affinity-query">
          <span>搜索商品、品牌或类目</span>
          <input
            id="affinity-query"
            name="affinity-query"
            className="text-input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="输入商品 ID、品牌或类目"
          />
        </label>
        <label htmlFor="affinity-relation-type">
          <span>关系类型</span>
          <select id="affinity-relation-type" name="affinity-relation-type" value={relationType} onChange={(event) => setRelationType(event.target.value)}>
            <option value="">全部关系</option>
            <option value="co_view">共同浏览</option>
            <option value="co_cart">共同加购</option>
            <option value="co_purchase">共同购买</option>
          </select>
        </label>
        <label htmlFor="affinity-opportunity-type">
          <span>机会类型</span>
          <select id="affinity-opportunity-type" name="affinity-opportunity-type" value={opportunityType} onChange={(event) => setOpportunityType(event.target.value)}>
            <option value="">全部机会</option>
            <option value="bundle">组合搭配</option>
            <option value="cross_sell">交叉销售</option>
            <option value="substitute">替代推荐</option>
            <option value="category_bridge">跨品类桥接</option>
          </select>
        </label>
      </section>

      <section className="forecast-main-grid visual-first-grid">
        <ChartPanel
          title="商品关系力导向图"
          subtitle="节点大小代表中心性，连线粗细代表支持度与提升度。"
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
              ? `已聚焦 ${selectedNode ? `${selectedNode.brand} ${selectedNode.entity_id}` : productLabel(selectedEntity)}，关系边已同步过滤。`
              : '点击节点或使用下方商品 chip 聚焦关系边。'
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
          actions={
            graphEvidence.nodes.length ? (
              <div className="filter-chip-row" aria-label="图谱节点键盘筛选">
                <button type="button" className="filter-chip" aria-pressed={!selectedEntity} onClick={() => setSelectedEntity('')}>
                  全部商品
                </button>
                {graphEvidence.nodes.slice(0, 8).map((node) => (
                  <button
                    type="button"
                    className="filter-chip"
                    aria-pressed={selectedEntity === node.id}
                    key={node.id}
                    onClick={() => setSelectedEntity(node.id)}
                  >
                    {node.name}
                  </button>
                ))}
              </div>
            ) : null
          }
        />

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>质量门禁</h2>
              <p>控制有效会话、图谱边和配对膨胀风险。</p>
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
            <dt>全部会话</dt>
            <dd>{number(quality.data?.session_count)}</dd>
            <dt>有效会话</dt>
            <dd>{number(quality.data?.eligible_session_count)}</dd>
            <dt>稀疏图谱</dt>
            <dd>{quality.data?.sparse_graph ? '是' : '否'}</dd>
          </dl>
        </article>
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
                  {(opportunities.data ?? []).map((row) => (
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
                  {opportunities.data?.length === 0 ? (
                    <tr>
                      <td colSpan={7}>当前筛选没有达到置信阈值的机会。</td>
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
