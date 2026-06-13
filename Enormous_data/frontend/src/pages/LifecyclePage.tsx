import { HeartPulse, Layers3, Target, UsersRound } from 'lucide-react';
import {
  useLifecycleCategoryAffinity,
  useLifecycleRiskQueue,
  useLifecycleRules,
  useLifecycleSegments,
  useLifecycleSummary,
} from '../api/hooks';
import { algorithmCopy, displayValue, label } from '../i18n/displayText';

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : '待生成';
}

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : '待生成';
}

function segmentTone(segment?: string) {
  if (segment === 'champion' || segment === 'high_value') return 'success';
  if (segment === 'cart_intent' || segment === 'at_risk') return 'warning';
  return 'queued';
}

export function LifecyclePage() {
  const summary = useLifecycleSummary();
  const segments = useLifecycleSegments();
  const riskQueue = useLifecycleRiskQueue(80);
  const affinity = useLifecycleCategoryAffinity(50);
  const rules = useLifecycleRules();
  const hasError = summary.isError || segments.isError || riskQueue.isError || affinity.isError || rules.isError;

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">用户生命周期智能</span>
        <h1>用户生命周期与价值分层</h1>
        <p>基于特征集市用户日级事实构建最近活跃、频次、价值、活跃度、偏好类目和运营动作队列。</p>
      </section>

      {hasError ? (
        <div className="error-banner" role="alert">
          用户生命周期缓存尚未生成，请先运行 Spark 刷新任务。
        </div>
      ) : null}

      <section className="ops-command-band">
        <div>
          <span className="status-pill tone-success">生命周期契约 v1</span>
          <h2>{summary.data?.run_id ? `运行 ${summary.data.run_id}` : '等待生命周期运行'}</h2>
          <p>快照 {summary.data?.snapshot_dt ?? '待生成'} · 监控用户 {number(summary.data?.user_count)}</p>
        </div>
        <UsersRound size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>高价值用户</span>
          <strong>{number(summary.data?.high_value_users)}</strong>
          <small>生命周期收入 {money(summary.data?.revenue)}</small>
        </article>
        <article className="metric-card tone-warning">
          <span>转化意图</span>
          <strong>{number(summary.data?.convert_intent_users)}</strong>
          <small>购物车召回候选</small>
        </article>
        <article className="metric-card tone-danger">
          <span>流失风险</span>
          <strong>{number(summary.data?.at_risk_users)}</strong>
          <small>平均最近活跃 {number(summary.data?.avg_recency_days)} 天</small>
        </article>
        <article className="metric-card">
          <span>购买次数</span>
          <strong>{number(summary.data?.purchase_count)}</strong>
          <small>{number(summary.data?.segment_count)} 个生命周期分层</small>
        </article>
      </section>

      <section className="ops-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>分层分布</h2>
              <p>按生命周期阶段聚合用户、收入和购买。</p>
            </div>
            <Layers3 size={20} />
          </div>
          <div className="quality-checks">
            {(segments.data ?? []).map((segment) => (
              <div className={`quality-check tone-${segmentTone(segment.lifecycle_segment)}`} key={segment.lifecycle_segment}>
                <span>{label('segment', segment.lifecycle_segment)}</span>
                <strong>{number(segment.users)} 个用户 · {money(segment.revenue)}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>规则解释</h2>
              <p>{algorithmCopy(rules.data?.model ?? '等待规则报告')}</p>
            </div>
            <HeartPulse size={20} />
          </div>
          <div className="quality-checks">
            {(rules.data?.rules ?? []).map((rule) => (
              <div className="quality-check tone-success" key={rule.name}>
                <span>{label('segment', rule.name, { fallback: rule.name })}</span>
                <strong>{rule.threshold}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>运营动作队列</h2>
            <p>按收入、购物车意图和行为强度排序的用户级证据。</p>
          </div>
          <Target size={20} />
        </div>
        <div className="table-scroll">
          <table aria-label="用户生命周期运营动作队列">
            <thead>
              <tr>
                <th>用户</th>
                <th>分层</th>
                <th>风险</th>
                <th>偏好类目</th>
                <th>会话</th>
                <th>浏览</th>
                <th>加购</th>
                <th>购买</th>
                <th>收入</th>
                <th>建议动作</th>
              </tr>
            </thead>
            <tbody>
              {(riskQueue.data ?? []).map((user) => (
                <tr key={user.user_id}>
                  <td>{user.user_id}</td>
                  <td><span className={`status-pill tone-${segmentTone(user.lifecycle_segment)}`}>{label('segment', user.lifecycle_segment)}</span></td>
                  <td>{label('risk', user.risk_band)}</td>
                  <td>{displayValue(user.preferred_category_level1)}</td>
                  <td>{number(user.sessions)}</td>
                  <td>{number(user.views)}</td>
                  <td>{number(user.carts)}</td>
                  <td>{number(user.purchases)}</td>
                  <td>{money(user.revenue)}</td>
                  <td>{algorithmCopy(user.recommended_action)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>偏好类目</h2>
            <p>用户偏好类目与类目收入对照。</p>
          </div>
        </div>
        <div className="table-scroll">
          <table aria-label="用户偏好类目">
            <thead>
              <tr>
                <th>类目</th>
                <th>用户数</th>
                <th>用户收入</th>
                <th>用户购买</th>
                <th>类目收入</th>
                <th>类目购买</th>
              </tr>
            </thead>
            <tbody>
              {(affinity.data ?? []).map((row) => (
                <tr key={row.category_level1 ?? 'unknown'}>
                  <td>{displayValue(row.category_level1)}</td>
                  <td>{number(row.users)}</td>
                  <td>{money(row.user_revenue)}</td>
                  <td>{number(row.user_purchases)}</td>
                  <td>{money(row.category_revenue)}</td>
                  <td>{number(row.category_purchases)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
