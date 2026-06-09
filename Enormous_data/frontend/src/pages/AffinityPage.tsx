import { GitBranch, Network, PackageSearch, ShieldCheck } from 'lucide-react';
import { useMemo, useState } from 'react';
import {
  useAffinityCommunities,
  useAffinityEdges,
  useAffinityNodes,
  useAffinityOpportunities,
  useAffinityQuality,
  useAffinitySummary,
} from '../api/hooks';
import type { AffinityEdge } from '../types/api';

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
  return typeof value === 'number' ? value.toFixed(3) : 'pending';
}

function statusTone(status?: string) {
  if (status === 'passed' || status === 'low') return 'success';
  if (status === 'needs_review' || status === 'medium') return 'queued';
  return 'failed';
}

function relationLabel(relation: string) {
  return {
    co_view: '共看',
    co_cart: '共加购',
    co_purchase: '共购',
  }[relation] ?? relation;
}

function edgeTitle(edge?: AffinityEdge | null) {
  if (!edge) return '等待关系边';
  return `${edge.source_label} → ${edge.target_label}`;
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
  const quality = useAffinityQuality();
  const hasError = summary.isError || nodes.isError || edges.isError || communities.isError || opportunities.isError || quality.isError;
  const strongest = summary.data?.strongest_edge ?? edges.data?.[0] ?? null;
  const selectedNode = useMemo(
    () => nodes.data?.find((node) => node.entity_id === selectedEntity) ?? nodes.data?.[0],
    [nodes.data, selectedEntity],
  );

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">Product affinity graph</span>
        <h1>商品关系图谱与搭配洞察</h1>
        <p>从真实 session 共看、共加购和共购关系中挖掘商品搭配、替代和跨类目机会，为推荐和商品运营提供证据。</p>
      </section>

      {hasError ? <div className="error-banner">商品关系图谱缓存尚未生成，请先运行 Spark 刷新任务。</div> : null}
      {summary.data?.sparse_graph ? (
        <div className="error-banner">当前图谱样本稀疏，仅保留低置信关系证据，不建议直接上线搭配或替代策略。</div>
      ) : null}

      <section className="ops-command-band">
        <div>
          <span className={`status-pill tone-${statusTone(summary.data?.quality_status)}`}>
            {summary.data?.quality_status ?? 'pending'}
          </span>
          <h2>{summary.data?.contract_version ?? 'product-affinity-graph/v1'}</h2>
          <p>{summary.data?.recommended_action ?? '等待商品关系图谱产物'}</p>
        </div>
        <Network size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>图谱边</span>
          <strong>{number(summary.data?.edge_count)}</strong>
          <small>{number(summary.data?.node_count)} product nodes</small>
        </article>
        <article className="metric-card">
          <span>机会队列</span>
          <strong>{number(summary.data?.opportunity_count)}</strong>
          <small>{number(summary.data?.community_count)} communities</small>
        </article>
        <article className="metric-card tone-warning">
          <span>可用 Session</span>
          <strong>{number(summary.data?.eligible_session_count)}</strong>
          <small>min support {number(summary.data?.min_support)}</small>
        </article>
        <article className="metric-card">
          <span>最强关系</span>
          <strong>{score(strongest?.lift)}</strong>
          <small>{strongest ? relationLabel(strongest.relation_type) : 'pending'}</small>
        </article>
      </section>

      <section className="toolbar forecast-toolbar" aria-label="商品关系筛选">
        <label>
          <span>搜索商品 / 品牌 / 类目</span>
          <input
            className="text-input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="samsung / electronics / product id"
          />
        </label>
        <label>
          <span>关系类型</span>
          <select value={relationType} onChange={(event) => setRelationType(event.target.value)}>
            <option value="">全部</option>
            <option value="co_view">共看</option>
            <option value="co_cart">共加购</option>
            <option value="co_purchase">共购</option>
          </select>
        </label>
        <label>
          <span>机会类型</span>
          <select value={opportunityType} onChange={(event) => setOpportunityType(event.target.value)}>
            <option value="">全部</option>
            <option value="bundle">搭配</option>
            <option value="cross_sell">交叉销售</option>
            <option value="substitute">替代</option>
            <option value="category_bridge">跨类目</option>
          </select>
        </label>
      </section>

      <section className="forecast-main-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>关系探索</h2>
              <p>选择商品后查看它的邻居边；该表是图谱的可访问替代视图。</p>
            </div>
            <GitBranch size={20} />
          </div>
          <div className="affinity-node-list" aria-label="商品节点列表">
            {(nodes.data ?? []).slice(0, 8).map((node) => (
              <button
                className={`affinity-node ${selectedEntity === node.entity_id ? 'active' : ''}`}
                type="button"
                key={node.entity_id}
                onClick={() => setSelectedEntity(node.entity_id)}
              >
                <strong>{node.entity_label}</strong>
                <span>{node.brand} · {node.category_level1}</span>
                <small>{money(node.revenue)} · degree {number(node.degree)}</small>
              </button>
            ))}
            {nodes.data?.length === 0 ? <p className="empty-copy">当前搜索没有匹配商品。</p> : null}
          </div>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>质量门禁</h2>
              <p>控制 eligible session、edge count 和稀疏图谱状态。</p>
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
            <dt>Session</dt>
            <dd>{number(quality.data?.session_count)}</dd>
            <dt>Eligible</dt>
            <dd>{number(quality.data?.eligible_session_count)}</dd>
            <dt>Sparse</dt>
            <dd>{quality.data?.sparse_graph ? 'yes' : 'no'}</dd>
          </dl>
        </article>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>邻居关系边</h2>
            <p>{edgeTitle(strongest)}，每条边保留 support、confidence、lift、jaccard 和 revenue overlap。</p>
          </div>
        </div>
        <div className="table-scroll">
          <table aria-label="商品关系边">
            <thead>
              <tr>
                <th>源商品</th>
                <th>目标商品</th>
                <th>关系</th>
                <th>Support</th>
                <th>Confidence</th>
                <th>Lift</th>
                <th>Jaccard</th>
                <th>Revenue overlap</th>
              </tr>
            </thead>
            <tbody>
              {(edges.data ?? []).map((edge) => (
                <tr key={`${edge.source_id}-${edge.target_id}-${edge.relation_type}`}>
                  <td>{edge.source_label}</td>
                  <td>{edge.target_label}</td>
                  <td><span className="event-chip">{relationLabel(edge.relation_type)}</span></td>
                  <td>{number(edge.support)}</td>
                  <td>{percent(edge.confidence)}</td>
                  <td>{score(edge.lift)}</td>
                  <td>{score(edge.jaccard)}</td>
                  <td>{money(edge.revenue_overlap)}</td>
                </tr>
              ))}
              {edges.data?.length === 0 ? (
                <tr>
                  <td colSpan={8}>当前筛选没有关系边。</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="ops-grid">
        <article className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>搭配与替代机会</h2>
              <p>把高 lift 关系转成可复核运营动作。</p>
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
                  <th>Lift</th>
                  <th>Support</th>
                  <th>收入池</th>
                  <th>动作</th>
                </tr>
              </thead>
              <tbody>
                {(opportunities.data ?? []).map((row) => (
                  <tr key={row.opportunity_id}>
                    <td><span className={`status-pill tone-${statusTone(row.risk_level)}`}>{row.type}</span></td>
                    <td>{row.primary_label}</td>
                    <td>{row.related_label}</td>
                    <td>{score(row.lift)}</td>
                    <td>{number(row.support)}</td>
                    <td>{money(row.estimated_revenue_pool)}</td>
                    <td>{row.action}</td>
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
              <h2>社群证据</h2>
              <p>按类目社群汇总节点、边和收入规模。</p>
            </div>
          </div>
          <div className="quality-checks">
            {(communities.data ?? []).slice(0, 6).map((community) => (
              <div className="quality-check tone-success" key={community.community_id}>
                <span>{community.category_level1}</span>
                <strong>{number(community.node_count)} nodes · {number(community.edge_count)} edges</strong>
              </div>
            ))}
          </div>
          <dl>
            <dt>Selected node</dt>
            <dd>{selectedNode ? `${selectedNode.entity_id} · ${selectedNode.brand}` : 'none'}</dd>
            <dt>Community</dt>
            <dd>{selectedNode?.community_id ?? 'none'}</dd>
          </dl>
        </article>
      </section>
    </>
  );
}
