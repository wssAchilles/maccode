import { Boxes, Clock3, DatabaseZap, GitBranch, ShieldCheck } from 'lucide-react';
import {
  useFeatureMartCategories,
  useFeatureMartFreshness,
  useFeatureMartPartitions,
  useFeatureMartProducts,
  useFeatureMartQuality,
  useFeatureMartSummary,
  useFeatureMartUsers,
} from '../api/hooks';

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : 'pending';
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(2)}%` : 'pending';
}

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : 'pending';
}

function hours(value?: number | null) {
  if (typeof value !== 'number') {
    return 'pending';
  }
  return value >= 24 ? `${(value / 24).toFixed(1)} days` : `${value.toFixed(1)} hours`;
}

function statusTone(status?: string) {
  if (status === 'passed' || status === 'written') return 'succeeded';
  if (status === 'failed' || status === 'stale') return 'failed';
  return 'queued';
}

export function FeatureMartPage() {
  const summary = useFeatureMartSummary();
  const freshness = useFeatureMartFreshness();
  const quality = useFeatureMartQuality();
  const partitions = useFeatureMartPartitions();
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

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">Behavior feature mart</span>
        <h1>湖仓级行为事实与特征层</h1>
        <p>把真实 Kaggle 行为日志沉淀为可重跑、可审计、可被推荐和实验复用的日级事实/特征产物。</p>
      </section>

      {hasError ? (
        <div className="error-banner" role="alert">
          Feature Mart 缓存尚未生成，请先运行 Spark 刷新任务。
        </div>
      ) : null}

      <section className="ops-command-band">
        <div>
          <span aria-label={`质量状态：${summary.data?.quality_status ?? 'pending'}`} className={`status-pill tone-${statusTone(summary.data?.quality_status)}`}>
            {summary.data?.quality_status ?? 'pending'}
          </span>
          <h2>{summary.data?.contract_version ?? 'behavior-feature-mart/v1'}</h2>
          <p>
            {summary.data?.run_id ?? 'waiting for feature mart'} · {summary.data?.date_range.min_dt ?? 'pending'} to{' '}
            {summary.data?.date_range.max_dt ?? 'pending'}
          </p>
        </div>
        <DatabaseZap size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>写入分区</span>
          <strong>{number(summary.data?.partitions.written)}</strong>
          <small>{number(summary.data?.partitions.expected)} expected partitions</small>
        </article>
        <article className="metric-card">
          <span>去重事件</span>
          <strong>{number(summary.data?.deduped_event_rows)}</strong>
          <small>{number(summary.data?.cleaned_rows)} cleaned rows</small>
        </article>
        <article className="metric-card">
          <span>Freshness SLA</span>
          <strong>{freshness.data?.sla_status ?? summary.data?.freshness.sla_status ?? 'pending'}</strong>
          <small>{hours(freshness.data?.freshness_lag_hours ?? summary.data?.freshness.freshness_lag_hours)} lag</small>
        </article>
        <article className="metric-card tone-warning">
          <span>迟到数据</span>
          <strong>{number(freshness.data?.late_rows)}</strong>
          <small>{percent(freshness.data?.late_rate)} late rate</small>
        </article>
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
                <span>{check.name}</span>
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
            <dd>{partitions.data?.min_dt ?? 'pending'}</dd>
            <dt>最新分区</dt>
            <dd>{partitions.data?.max_dt ?? 'pending'}</dd>
            <dt>水位时间</dt>
            <dd>{freshness.data?.watermark_time ?? 'pending'}</dd>
            <dt>缺失分区</dt>
            <dd>{partitions.data?.missing.length ? partitions.data.missing.join(', ') : 'none'}</dd>
          </dl>
          <div className="partition-strip" aria-label="Feature mart partitions">
            {(partitions.data?.partitions ?? []).slice(0, 32).map((partition) => (
              <span
                aria-label={`${partition.dt}, ${partition.status}, ${number(partition.rows)} rows`}
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

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>商品特征预览</h2>
            <p>daily_product_behavior，用于推荐、优化和异常检测复用。</p>
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
                <th>GMV</th>
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

      <section className="ops-grid">
        <article className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>类目特征</h2>
              <p>daily_category_behavior 聚合结果。</p>
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
                  <th>GMV</th>
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
              <p>daily_user_behavior 聚合结果。</p>
            </div>
            <Clock3 size={20} />
          </div>
          <div className="table-scroll">
            <table aria-label="用户特征预览">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>用户</th>
                  <th>Session</th>
                  <th>浏览</th>
                  <th>购买</th>
                  <th>GMV</th>
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
                    <td>{row.preferred_category_level1 ?? 'unknown'}</td>
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
