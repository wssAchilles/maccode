import { Footprints, GitFork, Route, Signpost } from 'lucide-react';
import {
  useJourneyExitEvents,
  useJourneyPaths,
  useJourneyPurchasePaths,
  useJourneySummary,
  useJourneyTransitions,
} from '../api/hooks';
import { algorithmCopy, label } from '../i18n/displayText';

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : '待生成';
}

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : '待生成';
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(2)}%` : '待生成';
}

function seconds(value?: number | null) {
  if (typeof value !== 'number') return '待生成';
  return value >= 60 ? `${(value / 60).toFixed(1)} 分钟` : `${value.toFixed(0)} 秒`;
}

function hintTone(hint?: string) {
  if (hint === 'inspect friction') return 'warning';
  if (hint === 'conversion step') return 'success';
  return 'queued';
}

function eventLabel(value: string) {
  return label('eventType', value, { fallback: value });
}

function pathLabel(value: string) {
  return value
    .split(/\s*(?:>|→)\s*/)
    .filter(Boolean)
    .map(eventLabel)
    .join(' → ');
}

export function JourneyPage() {
  const summary = useJourneySummary();
  const paths = useJourneyPaths(80);
  const transitions = useJourneyTransitions(80);
  const exits = useJourneyExitEvents(40);
  const purchasePaths = useJourneyPurchasePaths(40);
  const hasError = summary.isError || paths.isError || transitions.isError || exits.isError || purchasePaths.isError;

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">用户旅程智能</span>
        <h1>用户旅程路径智能</h1>
        <p>从会话事件序列挖掘高频路径、事件转移、退出点和购买前路径，定位转化断点。</p>
      </section>

      {hasError ? <div className="error-banner">旅程路径缓存尚未生成，请先运行 Spark 刷新任务。</div> : null}

      <section className="ops-command-band">
        <div>
          <span className="status-pill tone-success">旅程路径契约 v1</span>
          <h2>{summary.data?.run_id ? `运行 ${summary.data.run_id}` : '等待旅程运行'}</h2>
          <p>{summary.data?.recommended_action ? algorithmCopy(summary.data.recommended_action) : '等待路径诊断结果'}</p>
        </div>
        <Route size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card">
          <span>会话路径</span>
          <strong>{number(summary.data?.unique_paths)}</strong>
          <small>{number(summary.data?.sessions)} 个会话</small>
        </article>
        <article className="metric-card tone-success">
          <span>购买路径率</span>
          <strong>{percent(summary.data?.purchase_path_rate)}</strong>
          <small>{number(summary.data?.purchase_sessions)} 个购买会话</small>
        </article>
        <article className="metric-card tone-warning">
          <span>加购路径率</span>
          <strong>{percent(summary.data?.cart_path_rate)}</strong>
          <small>{number(summary.data?.cart_sessions)} 个加购会话</small>
        </article>
        <article className="metric-card">
          <span>平均步数</span>
          <strong>{number(summary.data?.avg_steps)}</strong>
          <small>平均耗时 {seconds(summary.data?.avg_duration_seconds)}</small>
        </article>
      </section>

      <section className="ops-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>关键转移</h2>
              <p>从事件 A 到事件 B 的流量、购买率和摩擦提示。</p>
            </div>
            <GitFork size={20} />
          </div>
          <div className="quality-checks">
            {(transitions.data ?? []).slice(0, 6).map((row) => (
              <div className={`quality-check tone-${hintTone(row.dropoff_hint)}`} key={`${row.from_event}-${row.to_event}`}>
                <span>{eventLabel(row.from_event)} → {eventLabel(row.to_event)}</span>
                <strong>{number(row.transitions)} · {percent(row.conversion_rate)}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>退出事件</h2>
              <p>识别高占比退出点，优先调查移出购物车和纯浏览退出。</p>
            </div>
            <Signpost size={20} />
          </div>
          <div className="quality-checks">
            {(exits.data ?? []).slice(0, 6).map((row) => (
              <div className={`quality-check tone-${row.purchase_rate > 0 ? 'success' : 'warning'}`} key={row.last_event}>
                <span>{eventLabel(row.last_event)}</span>
                <strong>{number(row.sessions)} · {percent(row.exit_share)}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>高频路径</h2>
            <p>按会话数、收入和购买率排序的路径模式。</p>
          </div>
          <Footprints size={20} />
        </div>
        <div className="table-scroll">
          <table aria-label="用户旅程高频路径">
            <thead>
              <tr>
                <th>路径</th>
                <th>会话</th>
                <th>加购会话</th>
                <th>购买会话</th>
                <th>购买率</th>
                <th>收入</th>
                <th>平均步数</th>
                <th>平均耗时</th>
              </tr>
            </thead>
            <tbody>
              {(paths.data ?? []).map((row) => (
                <tr key={row.path_signature}>
                  <td>{pathLabel(row.path_signature)}</td>
                  <td>{number(row.sessions)}</td>
                  <td>{number(row.cart_sessions)}</td>
                  <td>{number(row.purchase_sessions)}</td>
                  <td>{percent(row.conversion_rate)}</td>
                  <td>{money(row.revenue)}</td>
                  <td>{number(row.avg_steps)}</td>
                  <td>{seconds(row.avg_duration_seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>购买前路径</h2>
            <p>只看包含购买的路径，帮助总结正向转化经验。</p>
          </div>
        </div>
        <div className="table-scroll">
          <table aria-label="购买前路径">
            <thead>
              <tr>
                <th>路径</th>
                <th>购买会话</th>
                <th>收入</th>
                <th>平均步数</th>
                <th>平均耗时</th>
              </tr>
            </thead>
            <tbody>
              {(purchasePaths.data ?? []).map((row) => (
                <tr key={row.path_signature}>
                  <td>{pathLabel(row.path_signature)}</td>
                  <td>{number(row.purchase_sessions)}</td>
                  <td>{money(row.revenue)}</td>
                  <td>{number(row.avg_steps)}</td>
                  <td>{seconds(row.avg_duration_seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
