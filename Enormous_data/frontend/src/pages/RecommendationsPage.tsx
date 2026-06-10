import { BellRing, RotateCcw, ShieldCheck } from 'lucide-react';
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

function riskTone(value: 'success' | 'warning' | 'danger') {
  return value;
}

function statusTone(status: string) {
  if (status === 'passed') return 'success';
  if (status.includes('degraded') || status.includes('review')) return 'warning';
  return 'danger';
}

export function RecommendationsPage() {
  const summary = useRecommendationSummary();
  const items = useRecommendationItems(50);
  const quality = useRecommendationQuality();
  const alerts = useRecommendationAlerts();
  const hasError = summary.isError || items.isError || quality.isError || alerts.isError;
  const status = summary.data?.quality_status ?? 'pending';
  const alertRows = alerts.data ?? [];
  const fallbackTone = riskTone((summary.data?.fallback_rate ?? 0) > 0.4 ? 'danger' : (summary.data?.fallback_rate ?? 0) > 0.2 ? 'warning' : 'success');
  const confidenceTone = riskTone((summary.data?.avg_confidence ?? 0) < 0.1 ? 'danger' : (summary.data?.avg_confidence ?? 0) < 0.3 ? 'warning' : 'success');
  const freshnessTone = riskTone((summary.data?.freshness_lag_minutes ?? 0) > 10080 ? 'danger' : (summary.data?.freshness_lag_minutes ?? 0) > 1440 ? 'warning' : 'success');
  const hasBlockingRisk = [fallbackTone, confidenceTone, freshnessTone].includes('danger') || alertRows.length > 0;
  const canPromote = status === 'passed' && !hasBlockingRisk;
  const publishStatus = canPromote ? status : 'needs review';

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">Nearline recommendation guardrails</span>
        <h1>准实时推荐与监控守护</h1>
        <p>用 Spark 生成可解释推荐快照，并通过质量门禁、fallback 和回滚状态控制前端可见结果。</p>
      </section>

      {hasError ? <div className="error-banner">推荐缓存尚未生成，请先运行 Spark 刷新任务。</div> : null}

      <section className="recommendation-triage-grid" aria-label="推荐发布风险摘要">
        <article className={`triage-card tone-${canPromote ? statusTone(status) : 'warning'}`}>
          <span>发布状态</span>
          <strong>{publishStatus}</strong>
          <small>{summary.data?.contract_version ?? 'nearline-recommendation/v1'} · quality {status}</small>
          <p>{canPromote ? '门禁通过，可以发布当前快照。' : '存在发布风险，先处理风险原因。'}</p>
        </article>
        <article className="triage-card tone-danger">
          <span>风险原因</span>
          <div className="risk-list">
            <RiskRow label="fallback" value={percent(summary.data?.fallback_rate)} tone={fallbackTone} />
            <RiskRow label="confidence" value={percent(summary.data?.avg_confidence)} tone={confidenceTone} />
            <RiskRow label="freshness" value={freshness(summary.data?.freshness_lag_minutes)} tone={freshnessTone} />
            {alertRows.length ? alertRows.map((alert) => <RiskRow key={alert.alert_code} label={alert.metric} value={alert.message} tone={alert.severity === 'critical' ? 'danger' : 'warning'} />) : null}
          </div>
        </article>
        <article className={`triage-card tone-${summary.data?.rollback_ready ? 'warning' : 'danger'}`}>
          <span>回滚动作</span>
          <strong>{summary.data?.rollback_ready ? 'rollback ready' : 'no snapshot'}</strong>
          <small>promotion gate {canPromote ? 'clear' : 'blocked'}</small>
          <p>{summary.data?.previous_snapshot_path ?? '缺少上一版快照时，不应自动发布失败结果。'}</p>
        </article>
        <article className="triage-card tone-success">
          <span>快照证据</span>
          <strong>{number(summary.data?.recommendation_count)}</strong>
          <small>{number(summary.data?.covered_sessions)} covered sessions</small>
          <p>{summary.data?.active_snapshot_path ?? '等待 active snapshot'}</p>
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

function RiskRow({ label, tone, value }: { label: string; tone: 'success' | 'warning' | 'danger'; value: string }) {
  return (
    <div className={`risk-row tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
