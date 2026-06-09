import { FlaskConical, GitBranch, ListChecks, ShieldCheck } from 'lucide-react';
import {
  useExperimentAssignments,
  useExperimentCatalog,
  useExperimentGuardrails,
  useExperimentSegments,
  useExperimentSummary,
} from '../api/hooks';

function number(value: unknown) {
  if (typeof value === 'number') return value.toLocaleString();
  return value == null ? 'pending' : String(value);
}

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : 'pending';
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : 'pending';
}

function statusTone(status?: string) {
  if (status === 'passed' || status === 'ready') return 'success';
  if (status === 'needs_review') return 'warning';
  return 'queued';
}

export function ExperimentsPage() {
  const summary = useExperimentSummary();
  const catalog = useExperimentCatalog();
  const assignments = useExperimentAssignments(80);
  const segments = useExperimentSegments();
  const guardrails = useExperimentGuardrails();
  const hasError = summary.isError || catalog.isError || assignments.isError || segments.isError || guardrails.isError;
  const guardrailStatus = summary.data?.guardrail_status ?? 'pending';

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">Growth experimentation</span>
        <h1>策略实验与效果评估</h1>
        <p>把生命周期、推荐和优化策略转成可审计的 A/B 分流、uplift 先验、实验护栏和执行清单。</p>
      </section>

      {hasError ? <div className="error-banner">实验评估缓存尚未生成，请先运行 Spark 刷新任务。</div> : null}

      <section className="ops-command-band">
        <div>
          <span className={`status-pill tone-${statusTone(guardrailStatus)}`}>{guardrailStatus}</span>
          <h2>{summary.data?.contract_version ?? 'growth-experimentation/v1'}</h2>
          <p>{summary.data?.run_id ?? 'waiting for experiment design'} · {summary.data?.causal_caveat ?? 'offline planning priors'}</p>
        </div>
        <FlaskConical size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>实验数</span>
          <strong>{number(summary.data?.experiment_count)}</strong>
          <small>{number(summary.data?.assigned_users)} assigned users</small>
        </article>
        <article className="metric-card">
          <span>实验分流</span>
          <strong>{percent(summary.data?.treatment_split)}</strong>
          <small>{number(summary.data?.treatment_assignments)} treatment / {number(summary.data?.control_assignments)} control</small>
        </article>
        <article className="metric-card tone-warning">
          <span>预期增量 GMV</span>
          <strong>{money(summary.data?.expected_incremental_gmv)}</strong>
          <small>{number(summary.data?.expected_incremental_purchases)} expected purchases</small>
        </article>
        <article className="metric-card">
          <span>推荐覆盖</span>
          <strong>{percent(summary.data?.recommendation_coverage.covered_sessions ? summary.data.recommendation_coverage.fallback_rate : null)}</strong>
          <small>{number(summary.data?.recommendation_coverage.recommendations)} recommendations</small>
        </article>
      </section>

      <section className="ops-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>实验目录</h2>
              <p>行业实验系统必须先定义目标人群、主指标、观测窗口和护栏。</p>
            </div>
            <GitBranch size={20} />
          </div>
          <div className="quality-checks">
            {(catalog.data ?? []).map((item) => (
              <div className={`quality-check tone-${statusTone(item.status)}`} key={item.experiment_key}>
                <span>{item.name}</span>
                <strong>{item.primary_metric} · {percent(item.expected_uplift_rate)}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>实验护栏</h2>
              <p>{guardrails.data?.recommended_action ?? '等待护栏报告'}</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <div className="quality-checks">
            {(guardrails.data?.checks ?? []).map((check) => (
              <div className={`quality-check tone-${check.passed ? 'success' : 'danger'}`} key={check.name}>
                <span>{check.name}</span>
                <strong>{number(check.actual)} {check.operator} {number(check.expected)}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>分层均衡</h2>
            <p>按实验、生命周期分层和 variant 检查样本分布，避免实验上线前就失衡。</p>
          </div>
          <ListChecks size={20} />
        </div>
        <div className="table-scroll">
          <table aria-label="实验分层均衡">
            <thead>
              <tr>
                <th>实验</th>
                <th>分层</th>
                <th>Variant</th>
                <th>用户数</th>
                <th>分层占比</th>
                <th>观测收入</th>
                <th>预期增量 GMV</th>
              </tr>
            </thead>
            <tbody>
              {(segments.data ?? []).map((row) => (
                <tr key={`${row.experiment_key}-${row.lifecycle_segment}-${row.variant}`}>
                  <td>{row.experiment_key}</td>
                  <td>{row.lifecycle_segment}</td>
                  <td><span className={`status-pill tone-${row.variant === 'treatment' ? 'success' : 'queued'}`}>{row.variant}</span></td>
                  <td>{number(row.users)}</td>
                  <td>{percent(row.segment_share)}</td>
                  <td>{money(row.observed_revenue)}</td>
                  <td>{money(row.expected_incremental_gmv)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>分流样本</h2>
            <p>稳定 hash 分桶生成 treatment/control，生产环境应保持 holdout 不可变。</p>
          </div>
        </div>
        <div className="table-scroll">
          <table aria-label="实验分流样本">
            <thead>
              <tr>
                <th>用户</th>
                <th>实验</th>
                <th>Variant</th>
                <th>Bucket</th>
                <th>生命周期</th>
                <th>风险</th>
                <th>类目</th>
                <th>预期购买增量</th>
                <th>预期 GMV</th>
              </tr>
            </thead>
            <tbody>
              {(assignments.data ?? []).map((row) => (
                <tr key={`${row.experiment_key}-${row.user_id}`}>
                  <td>{row.user_id}</td>
                  <td>{row.experiment_key}</td>
                  <td><span className={`status-pill tone-${row.variant === 'treatment' ? 'success' : 'queued'}`}>{row.variant}</span></td>
                  <td>{row.assignment_bucket.toFixed(4)}</td>
                  <td>{row.lifecycle_segment}</td>
                  <td>{row.risk_band}</td>
                  <td>{row.preferred_category_level1 ?? 'unknown'}</td>
                  <td>{percent(row.expected_incremental_purchase_prob)}</td>
                  <td>{money(row.expected_incremental_gmv)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
