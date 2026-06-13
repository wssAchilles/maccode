import { Boxes, Clock3, DatabaseZap, GitBranch, ShieldCheck } from 'lucide-react';
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
import { donutOption, horizontalBarOption } from '../lib/chartOptions';
import type { FeatureMartReadiness, NamedValue } from '../types/api';

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

function readinessRows(data?: FeatureMartReadiness): NamedValue[] {
  const ready = data?.ready_features ?? 0;
  const total = data?.total_features ?? 0;
  return [
    { name: '已就绪特征', value: ready },
    { name: '待修复特征', value: Math.max(0, total - ready) },
  ].filter((row) => row.value > 0);
}

function checkRows(data?: FeatureMartReadiness): NamedValue[] {
  return (data?.checks ?? []).map((check) => ({ name: fieldLabel(check.name), value: check.passed ? 1 : 0 }));
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
    const yOffset = peers.length === 1 ? 0 : (peerIndex - (peers.length - 1) / 2) * 70;
    return {
      id: nodeId,
      name: label('lineage', nodeId, { fallback: nodeId }),
      x: layer * 170,
      y: 120 + yOffset,
      symbolSize: layer === 0 || layer >= 3 ? 54 : 48,
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
        roam: false,
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 9],
        label: {
          show: true,
          position: 'bottom',
          color: '#dbe5ee',
          fontSize: 12,
          width: 96,
          overflow: 'break',
        },
        lineStyle: {
          color: '#8fb3cf',
          width: 2,
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

export function FeatureMartPage() {
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
  const readinessChartRows = readinessRows(readiness.data);
  const readinessCheckRows = checkRows(readiness.data);
  const lineageRows = readiness.data?.lineage ?? [];

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

      <section className="content-grid visual-first-grid">
        <ChartPanel
          title="特征就绪结构"
          subtitle="用就绪特征和待修复特征判断下游算法可用性"
          option={donutOption(readinessChartRows, '特征数')}
          isEmpty={!readinessChartRows.length}
          summary={`当前 ${number(readiness.data?.ready_features)} / ${number(readiness.data?.total_features)} 个特征就绪。`}
        />
        <ChartPanel
          title="质量检查矩阵"
          subtitle="用通过/未通过条形图替代长检查清单"
          option={horizontalBarOption(readinessCheckRows, '通过状态', '#56d27b')}
          isEmpty={!readinessCheckRows.length}
          summary={readiness.data ? `集市状态为 ${statusLabel(readiness.data.status)}。` : '等待就绪度评估。'}
        />
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>特征字典</h2>
              <p>用户可见字段只展示中文名、粒度、刷新频率和质量断言。</p>
            </div>
            <Boxes size={20} />
          </div>
          <div className="feature-dictionary-grid">
            {featureRows.slice(0, 6).map((feature) => (
              <div className="feature-dictionary-item" key={feature.feature_name}>
                <strong>{feature.chinese_name}</strong>
                <span>{grainLabel(feature.grain)} · {label('frequency', feature.refresh_frequency)}</span>
                <small>{feature.quality_assertions.map((item) => fieldLabel(item)).join('、')}</small>
              </div>
            ))}
            {featureRows.length === 0 ? <p className="empty-copy">等待特征字典。</p> : null}
          </div>
        </article>
        <ChartPanel
          title="特征血缘图"
          subtitle="从原始行为日志到下游算法的产物流向。"
          chartId="feature-mart-lineage-dag"
          option={featureLineageOption(lineageRows)}
          isEmpty={!lineageRows.length}
          summary={lineageRows.length ? `当前血缘图覆盖 ${lineageRows.length} 条产物依赖边。` : '等待血缘数据。'}
        />
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
