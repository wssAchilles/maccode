import { Boxes, Cpu, Layers3, PackageCheck, ShieldCheck } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useOptimizationCandidates, useOptimizationPlan, useOptimizationQuality, useOptimizationSummary, useTopCategories } from '../api/hooks';
import { algorithmCopy, displayValue, label, statusLabel } from '../i18n/displayText';
import type { OptimizationCandidate, OptimizationPlanItem } from '../types/api';

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '待生成';
}

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : '待生成';
}

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : '待生成';
}

type CategorySummary = {
  category: string;
  eventCount: number;
  candidateCount: number;
  selectedCount: number;
  expectedGmv: number;
  baselineGmv: number;
  averageRisk: number | null;
  topBrand: string;
};

type RepresentativeRow =
  | { source: 'selected'; item: OptimizationPlanItem }
  | { source: 'candidate'; item: OptimizationCandidate };

function categoryKey(value?: string | null) {
  return value || 'unknown';
}

function average(values: number[]) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

export function OptimizationPage() {
  const summary = useOptimizationSummary();
  const plan = useOptimizationPlan(50);
  const candidates = useOptimizationCandidates(100);
  const topCategories = useTopCategories();
  const quality = useOptimizationQuality();
  const hasError = summary.isError || plan.isError || quality.isError;
  const solverStatus = summary.data?.solver_status ?? 'pending';
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const categorySummaries = useMemo<CategorySummary[]>(() => {
    const categoryOrder = new Map<string, number>();
    const categories = new Set<string>();
    (topCategories.data ?? []).forEach((row, index) => {
      const key = categoryKey(row.name);
      categoryOrder.set(key, index);
      categories.add(key);
    });
    (candidates.data ?? []).forEach((row) => categories.add(categoryKey(row.category_level1)));
    (plan.data ?? []).forEach((row) => categories.add(categoryKey(row.category_level1)));

    return Array.from(categories)
      .map((category) => {
        const categoryCandidates = (candidates.data ?? []).filter((row) => categoryKey(row.category_level1) === category);
        const selected = (plan.data ?? []).filter((row) => categoryKey(row.category_level1) === category);
        const brandCounts = [...categoryCandidates, ...selected].reduce<Record<string, number>>((acc, row) => {
          const brand = displayValue(row.brand);
          acc[brand] = (acc[brand] ?? 0) + 1;
          return acc;
        }, {});
        const topBrand = Object.entries(brandCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? '暂无';
        return {
          category,
          eventCount: topCategories.data?.find((row) => categoryKey(row.name) === category)?.value ?? 0,
          candidateCount: categoryCandidates.length,
          selectedCount: selected.length,
          expectedGmv: selected.reduce((sum, row) => sum + row.expected_incremental_gmv, 0),
          baselineGmv: categoryCandidates.reduce((sum, row) => sum + row.baseline_gmv, 0),
          averageRisk: average(selected.length ? selected.map((row) => row.risk_score) : categoryCandidates.map((row) => row.risk_score)),
          topBrand,
        };
      })
      .sort((a, b) => {
        const orderA = categoryOrder.get(a.category) ?? Number.MAX_SAFE_INTEGER;
        const orderB = categoryOrder.get(b.category) ?? Number.MAX_SAFE_INTEGER;
        if (orderA !== orderB) return orderA - orderB;
        return b.eventCount - a.eventCount;
      });
  }, [candidates.data, plan.data, topCategories.data]);
  const selectedCategory = categorySummaries.some((row) => row.category === activeCategory)
    ? activeCategory
    : categorySummaries[0]?.category ?? null;
  const selectedCategorySummary = categorySummaries.find((row) => row.category === selectedCategory);
  const maxCategoryCandidates = Math.max(...categorySummaries.map((row) => row.candidateCount), 1);
  const maxCategorySelected = Math.max(...categorySummaries.map((row) => row.selectedCount), 1);
  const representativeRows = useMemo<RepresentativeRow[]>(() => {
    if (!selectedCategory) return [];
    const selectedForCategory = (plan.data ?? []).filter((row) => categoryKey(row.category_level1) === selectedCategory);
    const selectedProductIds = new Set(
      selectedForCategory.map((row) => row.product_id),
    );
    const selectedRows: RepresentativeRow[] = selectedForCategory.map((item) => ({ source: 'selected', item }));
    const candidateRows: RepresentativeRow[] = (candidates.data ?? [])
      .filter((row) => categoryKey(row.category_level1) === selectedCategory && !selectedProductIds.has(row.product_id))
      .slice(0, Math.max(0, 8 - selectedRows.length))
      .map((item) => ({ source: 'candidate', item }));
    return [...selectedRows, ...candidateRows];
  }, [candidates.data, plan.data, selectedCategory]);

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">经营优化</span>
        <h1>促销预算与推荐位优化</h1>
        <p>基于商品转化表现和约束优化生成可解释运营方案；结果用于机会排序，不作为因果投资回报承诺。</p>
      </section>

      {hasError ? <div className="error-banner">优化缓存尚未生成，请先运行 Spark 刷新任务。</div> : null}

      <section className="ops-command-band">
        <div>
          <span className={`status-pill tone-${solverStatus === 'optimal' ? 'succeeded' : 'queued'}`}>{statusLabel(solverStatus)}</span>
          <h2>优化求解契约 v1</h2>
          <p>{summary.data?.causal_caveat ? algorithmCopy(summary.data.causal_caveat) : '等待优化结果'}</p>
        </div>
        <Cpu size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>预期增量成交额</span>
          <strong>{money(summary.data?.expected_incremental_gmv)}</strong>
          <small>{number(summary.data?.expected_incremental_purchases)} 次预期增量购买</small>
        </article>
        <article className="metric-card">
          <span>预算利用率</span>
          <strong>{percent(summary.data?.budget_utilization)}</strong>
          <small>{money(summary.data?.used_budget)} / {money(summary.data?.total_budget)}</small>
        </article>
        <article className="metric-card">
          <span>推荐位利用</span>
          <strong>{percent(summary.data?.slot_utilization)}</strong>
          <small>{number(summary.data?.used_slots)} / {number(summary.data?.slot_count)} 个推荐位</small>
        </article>
        <article className="metric-card tone-warning">
          <span>平均风险分</span>
          <strong>{percent(summary.data?.average_risk_score)}</strong>
          <small>最优差距 {summary.data?.optimality_gap ?? '暂无'}</small>
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
            <dd>{quality.data?.budget_feasible ? statusLabel('feasible') : statusLabel('pending')}</dd>
            <dt>推荐位约束</dt>
            <dd>{quality.data?.slot_feasible ? statusLabel('feasible') : statusLabel('pending')}</dd>
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
                <span>{label('action', name)}</span>
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

      <section className="data-panel jobs-panel optimization-category-panel">
        <div className="panel-title">
          <div>
            <h2>类目覆盖矩阵</h2>
            <p>展示主要类目的数据体量、候选池覆盖和最终入选状态；未入选类目不会展开商品清单。</p>
          </div>
          <Layers3 size={20} />
        </div>
        <div className="optimization-category-grid" aria-label="优化类目覆盖">
          {categorySummaries.map((row) => {
            const isActive = row.category === selectedCategory;
            const decisionTone = row.selectedCount > 0 ? 'selected' : row.candidateCount > 0 ? 'candidate' : 'uncovered';
            return (
              <button
                className={`optimization-category-card is-${decisionTone}${isActive ? ' is-active' : ''}`}
                key={row.category}
                type="button"
                onClick={() => setActiveCategory(row.category)}
                aria-pressed={isActive}
              >
                <span className="optimization-category-card__topline">
                  <strong>{displayValue(row.category)}</strong>
                  <small>{row.selectedCount > 0 ? '已入选' : row.candidateCount > 0 ? '候选观察' : '未进入候选'}</small>
                </span>
                <span className="optimization-category-card__metrics">
                  <span>
                    <small>候选 / 入选</small>
                    <b>{row.candidateCount} / {row.selectedCount}</b>
                  </span>
                  <span>
                    <small>代表品牌</small>
                    <b>{row.topBrand}</b>
                  </span>
                </span>
                <span className="optimization-category-bars" aria-hidden="true">
                  <i style={{ width: `${(row.candidateCount / maxCategoryCandidates) * 100}%` }} />
                  <i style={{ width: `${(row.selectedCount / maxCategorySelected) * 100}%` }} />
                </span>
              </button>
            );
          })}
        </div>
        <div className="optimization-category-legend" aria-label="类目覆盖图例">
          <span><i className="legend-dot is-selected" />已入选优化方案</span>
          <span><i className="legend-dot is-candidate" />仅进入候选池</span>
          <span><i className="legend-dot is-uncovered" />当前批次未进入候选池</span>
        </div>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>{selectedCategory ? `${displayValue(selectedCategory)} 代表商品` : '优化方案'}</h2>
            <p>
              {selectedCategorySummary
                ? `该类目候选 ${selectedCategorySummary.candidateCount} 个，入选 ${selectedCategorySummary.selectedCount} 个；入选项全部展示，候选项仅补充少量代表。`
                : '每个商品最多一个动作，满足预算、推荐位、类目和品牌约束。'}
            </p>
          </div>
          <PackageCheck size={20} />
        </div>
        <div className="optimization-category-summary">
          <article>
            <span>类目行为量</span>
            <strong>{number(selectedCategorySummary?.eventCount)}</strong>
          </article>
          <article>
            <span>候选机会额</span>
            <strong>{money(selectedCategorySummary?.baselineGmv)}</strong>
          </article>
          <article>
            <span>入选增量额</span>
            <strong>{money(selectedCategorySummary?.expectedGmv)}</strong>
          </article>
          <article>
            <span>平均风险</span>
            <strong>{percent(selectedCategorySummary?.averageRisk)}</strong>
          </article>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>状态</th>
                <th>商品</th>
                <th>品牌</th>
                <th>动作</th>
                <th>成本</th>
                <th>机会成交额</th>
                <th>置信权重</th>
                <th>风险</th>
              </tr>
            </thead>
            <tbody>
              {representativeRows.map(({ source, item }) => {
                const selected = source === 'selected';
                return (
                  <tr key={`${source}-${item.product_id}`}>
                    <td><span className={`event-chip ${selected ? 'tone-success' : ''}`}>{selected ? '已入选' : '候选'}</span></td>
                    <td>{item.product_id}</td>
                    <td>{displayValue(item.brand)}</td>
                    <td><span className="event-chip">{selected ? label('action', item.action) : '候选观察'}</span></td>
                    <td>{selected ? money(item.cost) : '未分配'}</td>
                    <td>{money(selected ? item.expected_incremental_gmv : item.baseline_gmv)}</td>
                    <td>{percent(item.confidence_weight)}</td>
                    <td>{percent(item.risk_score)}</td>
                  </tr>
                );
              })}
              {representativeRows.length === 0 ? (
                <tr>
                  <td colSpan={8}>该类目当前批次没有代表商品，说明它未进入本轮候选池或优化缓存尚未生成。</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
