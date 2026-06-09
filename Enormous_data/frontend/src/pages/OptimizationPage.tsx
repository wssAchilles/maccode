import { Boxes, Cpu, ShieldCheck } from 'lucide-react';
import { useOptimizationPlan, useOptimizationQuality, useOptimizationSummary } from '../api/hooks';

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : 'pending';
}

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : 'pending';
}

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : 'pending';
}

export function OptimizationPage() {
  const summary = useOptimizationSummary();
  const plan = useOptimizationPlan(50);
  const quality = useOptimizationQuality();
  const hasError = summary.isError || plan.isError || quality.isError;
  const solverStatus = summary.data?.solver_status ?? 'pending';

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">Merchandising optimization</span>
        <h1>促销预算与推荐位优化</h1>
        <p>基于商品转化表现和约束优化生成可解释运营方案；结果用于机会排序，不作为因果 ROI 承诺。</p>
      </section>

      {hasError ? <div className="error-banner">优化缓存尚未生成，请先运行 Spark 刷新任务。</div> : null}

      <section className="ops-command-band">
        <div>
          <span className={`status-pill tone-${solverStatus === 'optimal' ? 'succeeded' : 'queued'}`}>{solverStatus}</span>
          <h2>{summary.data?.contract_version ?? 'merchandising-optimization/v1'}</h2>
          <p>{summary.data?.causal_caveat ?? '等待优化结果'}</p>
        </div>
        <Cpu size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>预期增量 GMV</span>
          <strong>{money(summary.data?.expected_incremental_gmv)}</strong>
          <small>{number(summary.data?.expected_incremental_purchases)} expected purchases</small>
        </article>
        <article className="metric-card">
          <span>预算利用率</span>
          <strong>{percent(summary.data?.budget_utilization)}</strong>
          <small>{money(summary.data?.used_budget)} / {money(summary.data?.total_budget)}</small>
        </article>
        <article className="metric-card">
          <span>推荐位利用</span>
          <strong>{percent(summary.data?.slot_utilization)}</strong>
          <small>{number(summary.data?.used_slots)} / {number(summary.data?.slot_count)} slots</small>
        </article>
        <article className="metric-card tone-warning">
          <span>平均风险分</span>
          <strong>{percent(summary.data?.average_risk_score)}</strong>
          <small>gap {summary.data?.optimality_gap ?? 'n/a'}</small>
        </article>
      </section>

      <section className="ops-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>求解器质量</h2>
              <p>预算、推荐位和候选集约束状态。</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <dl>
            <dt>候选商品</dt>
            <dd>{number(quality.data?.candidate_count)}</dd>
            <dt>可选商品</dt>
            <dd>{number(quality.data?.eligible_count)}</dd>
            <dt>已选商品</dt>
            <dd>{number(quality.data?.selected_count)}</dd>
            <dt>预算约束</dt>
            <dd>{quality.data?.budget_feasible ? 'feasible' : 'pending'}</dd>
            <dt>推荐位约束</dt>
            <dd>{quality.data?.slot_feasible ? 'feasible' : 'pending'}</dd>
          </dl>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>动作分配</h2>
              <p>按投放动作和类目汇总。</p>
            </div>
            <Boxes size={20} />
          </div>
          <div className="quality-checks">
            {Object.entries(summary.data?.action_allocation ?? {}).map(([name, value]) => (
              <div className="quality-check tone-success" key={name}>
                <span>{name}</span>
                <strong>{value}</strong>
              </div>
            ))}
            {Object.entries(summary.data?.category_allocation ?? {}).map(([name, value]) => (
              <div className="quality-check" key={name}>
                <span>{name}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>优化方案</h2>
            <p>每个商品最多一个动作，满足预算、推荐位、类目和品牌约束。</p>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>商品</th>
                <th>品牌</th>
                <th>类目</th>
                <th>动作</th>
                <th>成本</th>
                <th>预期增量 GMV</th>
                <th>置信权重</th>
                <th>风险</th>
              </tr>
            </thead>
            <tbody>
              {(plan.data ?? []).map((row) => (
                <tr key={`${row.product_id}-${row.action}`}>
                  <td>{row.product_id}</td>
                  <td>{row.brand}</td>
                  <td>{row.category_level1}</td>
                  <td><span className="event-chip">{row.action}</span></td>
                  <td>{money(row.cost)}</td>
                  <td>{money(row.expected_incremental_gmv)}</td>
                  <td>{percent(row.confidence_weight)}</td>
                  <td>{percent(row.risk_score)}</td>
                </tr>
              ))}
              {plan.data?.length === 0 ? (
                <tr>
                  <td colSpan={8}>等待优化方案</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
