import { BellRing, RotateCcw, ShieldCheck, Sparkles } from 'lucide-react';
import {
  useRecommendationAlerts,
  useRecommendationItems,
  useRecommendationQuality,
  useRecommendationSummary,
} from '../api/hooks';

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : 'pending';
}

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : 'pending';
}

function score(value: unknown) {
  if (typeof value === 'number') return value.toFixed(4);
  return value == null ? 'pending' : String(value);
}

function freshness(minutes?: number | null) {
  if (typeof minutes !== 'number') {
    return 'pending';
  }
  const days = minutes / 1440;
  return days >= 1 ? `${days.toFixed(1)} days` : `${minutes.toFixed(0)} minutes`;
}

export function RecommendationsPage() {
  const summary = useRecommendationSummary();
  const items = useRecommendationItems(50);
  const quality = useRecommendationQuality();
  const alerts = useRecommendationAlerts();
  const hasError = summary.isError || items.isError || quality.isError || alerts.isError;
  const status = summary.data?.quality_status ?? 'pending';
  const statusTone = status === 'passed' ? 'succeeded' : status.includes('degraded') ? 'queued' : 'failed';

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">Nearline recommendation guardrails</span>
        <h1>准实时推荐与监控守护</h1>
        <p>用 Spark 生成可解释推荐快照，并通过质量门禁、fallback 和回滚状态控制前端可见结果。</p>
      </section>

      {hasError ? <div className="error-banner">推荐缓存尚未生成，请先运行 Spark 刷新任务。</div> : null}

      <section className="ops-command-band">
        <div>
          <span className={`status-pill tone-${statusTone}`}>{status}</span>
          <h2>{summary.data?.contract_version ?? 'nearline-recommendation/v1'}</h2>
          <p>{summary.data?.run_id ?? 'waiting for recommendation snapshot'}</p>
        </div>
        <Sparkles size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>覆盖率</span>
          <strong>{percent(summary.data?.coverage_rate)}</strong>
          <small>{number(summary.data?.covered_sessions)} covered sessions</small>
        </article>
        <article className="metric-card">
          <span>个性化占比</span>
          <strong>{percent(summary.data?.personalized_rate)}</strong>
          <small>{number(summary.data?.recommendation_count)} recommendations</small>
        </article>
        <article className="metric-card tone-warning">
          <span>降级占比</span>
          <strong>{percent(summary.data?.fallback_rate)}</strong>
          <small>{summary.data?.rollback_ready ? 'rollback ready' : 'no previous snapshot'}</small>
        </article>
        <article className="metric-card">
          <span>平均置信度</span>
          <strong>{percent(summary.data?.avg_confidence)}</strong>
          <small>{freshness(summary.data?.freshness_lag_minutes)} freshness lag</small>
        </article>
      </section>

      <section className="ops-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>质量门禁</h2>
              <p>控制推荐覆盖、fallback、新鲜度、重复和非法商品。</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <div className="quality-checks">
            {(quality.data?.checks ?? []).map((check) => (
              <div className={`quality-check tone-${check.passed ? 'success' : 'danger'}`} key={check.name}>
                <span>{check.name}</span>
                <strong>{score(check.actual)} {check.operator} {score(check.expected)}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>告警与回滚</h2>
              <p>质量失败时保留上一版 active snapshot。</p>
            </div>
            <BellRing size={20} />
          </div>
          <div className="quality-checks">
            {(alerts.data ?? []).map((alert) => (
              <div className={`quality-check tone-${alert.severity === 'critical' ? 'danger' : 'warning'}`} key={alert.alert_code}>
                <span>{alert.metric}</span>
                <strong>{score(alert.actual)} / {score(alert.threshold)}</strong>
              </div>
            ))}
            {alerts.data?.length === 0 ? (
              <div className="quality-check tone-success">
                <span>promotion gate</span>
                <strong>clear</strong>
              </div>
            ) : null}
          </div>
          <dl>
            <dt>Active snapshot</dt>
            <dd>{summary.data?.active_snapshot_path ?? 'pending'}</dd>
            <dt>Previous snapshot</dt>
            <dd>{summary.data?.previous_snapshot_path ?? 'pending'}</dd>
          </dl>
        </article>
      </section>

      <section className="data-panel jobs-panel scroll-panel">
        <div className="panel-title">
          <div>
            <h2>推荐快照</h2>
            <p>按 session 输出 Top-K 商品，包含 reason code、来源和 fallback 标记。</p>
          </div>
          <RotateCcw size={20} />
        </div>
        <div className="table-scroll panel-scroll" aria-label="推荐快照滚动区域">
          <table>
            <thead>
              <tr>
                <th>Session</th>
                <th>Rank</th>
                <th>Product</th>
                <th>Brand</th>
                <th>Category</th>
                <th>Score</th>
                <th>Confidence</th>
                <th>Source</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {(items.data ?? []).map((row) => (
                <tr key={`${row.user_session}-${row.rank}-${row.product_id}`}>
                  <td>{row.user_session}</td>
                  <td>{row.rank}</td>
                  <td>{row.product_id}</td>
                  <td>{row.brand}</td>
                  <td>{row.category_level1}</td>
                  <td>{score(row.score)}</td>
                  <td>{percent(row.confidence)}</td>
                  <td><span className="event-chip">{row.source}</span></td>
                  <td>{row.reason_codes.join(', ')}</td>
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
    </>
  );
}
