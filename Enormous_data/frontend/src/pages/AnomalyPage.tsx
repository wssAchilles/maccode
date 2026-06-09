import { AlertTriangle, BellRing, Crosshair, Radar, ShieldCheck } from 'lucide-react';
import { useAnomalyAlerts, useAnomalyRules, useAnomalySummary, useAnomalyTimeline } from '../api/hooks';

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : 'pending';
}

function score(value?: number | null) {
  return typeof value === 'number' ? value.toFixed(2) : 'pending';
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : 'pending';
}

function tone(status?: string) {
  if (status === 'healthy' || status === 'passed') return 'success';
  if (status === 'critical' || status === 'failed') return 'danger';
  return 'warning';
}

export function AnomalyPage() {
  const summary = useAnomalySummary();
  const alerts = useAnomalyAlerts(80);
  const timeline = useAnomalyTimeline();
  const rules = useAnomalyRules();
  const hasError = summary.isError || alerts.isError || timeline.isError || rules.isError;

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">Ops anomaly radar</span>
        <h1>运营异常雷达</h1>
        <p>基于 Feature Mart 的日级商品和类目信号，用稳健基线识别收入、转化、流量和控制面异常。</p>
      </section>

      {hasError ? (
        <div className="error-banner" role="alert">
          异常雷达缓存尚未生成，请先运行 Spark 刷新任务。
        </div>
      ) : null}

      <section className="ops-command-band">
        <div>
          <span aria-label={`雷达状态：${summary.data?.radar_status ?? 'pending'}`} className={`status-pill tone-${tone(summary.data?.radar_status)}`}>
            {summary.data?.radar_status ?? 'pending'}
          </span>
          <h2>{summary.data?.contract_version ?? 'ops-anomaly-radar/v1'}</h2>
          <p>
            {summary.data?.run_id ?? 'waiting for anomaly radar'} · {summary.data?.date_range.min_dt ?? 'pending'} to{' '}
            {summary.data?.date_range.max_dt ?? 'pending'}
          </p>
        </div>
        <Radar size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-danger">
          <span>Critical</span>
          <strong>{number(summary.data?.critical_count)}</strong>
          <small>{number(summary.data?.alert_count)} total alerts</small>
        </article>
        <article className="metric-card tone-warning">
          <span>Warning</span>
          <strong>{number(summary.data?.warning_count)}</strong>
          <small>{number(summary.data?.watch_count)} watch signals</small>
        </article>
        <article className="metric-card">
          <span>监控实体</span>
          <strong>{number(summary.data?.monitored_entities)}</strong>
          <small>{number(summary.data?.signal_count)} daily signals</small>
        </article>
        <article className="metric-card">
          <span>最大稳健分数</span>
          <strong>{score(summary.data?.max_robust_z)}</strong>
          <small>{number(summary.data?.monitored_days)} monitored days</small>
        </article>
      </section>

      <section className="ops-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>Top alert</h2>
              <p>最高优先级异常和建议动作。</p>
            </div>
            <BellRing size={20} />
          </div>
          {summary.data?.top_alert ? (
            <dl>
              <dt>告警</dt>
              <dd>{summary.data.top_alert.alert_code}</dd>
              <dt>对象</dt>
              <dd>{summary.data.top_alert.entity_label}</dd>
              <dt>指标</dt>
              <dd>{summary.data.top_alert.metric}</dd>
              <dt>建议</dt>
              <dd>{summary.data.top_alert.recommended_action}</dd>
            </dl>
          ) : (
            <p className="empty-copy">当前没有异常告警。</p>
          )}
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>规则基线</h2>
              <p>{rules.data?.baseline ?? '等待规则报告'}</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <div className="quality-checks">
            {(rules.data?.rules ?? []).map((rule) => (
              <div className="quality-check tone-success" key={rule.name}>
                <Crosshair size={16} />
                <span>{rule.name}</span>
                <strong>{rule.threshold}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>异常时间线</h2>
            <p>按日聚合的异常信号强度。</p>
          </div>
          <AlertTriangle size={20} />
        </div>
        <div className="table-scroll">
          <table aria-label="异常时间线">
            <thead>
              <tr>
                <th>日期</th>
                <th>Signals</th>
                <th>Critical</th>
                <th>Warning</th>
                <th>Watch</th>
                <th>Max robust z</th>
              </tr>
            </thead>
            <tbody>
              {(timeline.data ?? []).map((row) => (
                <tr key={row.dt}>
                  <td>{row.dt}</td>
                  <td>{number(row.signal_count)}</td>
                  <td>{number(row.critical_count)}</td>
                  <td>{number(row.warning_count)}</td>
                  <td>{number(row.watch_count)}</td>
                  <td>{score(row.max_robust_z)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>告警证据</h2>
            <p>保留实际值、基线、偏移和建议动作，便于复盘。</p>
          </div>
        </div>
        <div className="table-scroll">
          <table aria-label="异常告警证据">
            <thead>
              <tr>
                <th>等级</th>
                <th>日期</th>
                <th>对象</th>
                <th>指标</th>
                <th>方向</th>
                <th>实际</th>
                <th>基线</th>
                <th>偏移</th>
                <th>Robust z</th>
                <th>建议动作</th>
              </tr>
            </thead>
            <tbody>
              {(alerts.data ?? []).map((alert) => (
                <tr key={`${alert.alert_code}-${alert.entity_id}-${alert.metric}`}>
                  <td>
                    <span className={`status-pill tone-${tone(alert.severity)}`}>{alert.severity}</span>
                  </td>
                  <td>{alert.dt ?? 'control'}</td>
                  <td>{alert.entity_label}</td>
                  <td>{alert.metric}</td>
                  <td>{alert.direction}</td>
                  <td>{number(alert.actual)}</td>
                  <td>{number(alert.baseline)}</td>
                  <td>{percent(alert.delta_rate)}</td>
                  <td>{score(alert.robust_z)}</td>
                  <td>{alert.recommended_action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
