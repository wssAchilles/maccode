import { Boxes, ChartNoAxesCombined, Gauge, Layers3, PackageSearch, ShieldCheck, Tags, Target } from 'lucide-react';
import { useMemo, useState } from 'react';
import {
  usePortfolioBrands,
  usePortfolioCategories,
  usePortfolioConcentration,
  usePortfolioOpportunities,
  usePortfolioPriceBands,
  usePortfolioProducts,
  usePortfolioQuality,
  usePortfolioSummary,
} from '../api/hooks';
import { algorithmCopy, displayValue, fieldLabel, label, listLabels, statusLabel } from '../i18n/displayText';
import type { PortfolioCategoryMix, PortfolioPriceBand } from '../types/api';

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : '待生成';
}

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : '待生成';
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '待生成';
}

function score(value?: number | null) {
  return typeof value === 'number' ? value.toFixed(4) : '待生成';
}

function statusTone(status?: string) {
  if (status === 'passed' || status === 'low') return 'success';
  if (status === 'needs_review' || status === 'medium') return 'queued';
  return 'failed';
}

function priceBandMatrix(rows: PortfolioPriceBand[]) {
  const categories = Array.from(new Set(rows.map((row) => row.category_level1))).sort();
  const bands = Array.from(new Set(rows.map((row) => row.price_band))).sort();
  const byKey = new Map(rows.map((row) => [`${row.category_level1}:${row.price_band}`, row]));
  return { categories, bands, byKey };
}

function priceBandLabel(value: unknown) {
  const raw = String(value ?? '').trim();
  const labels: Record<string, string> = {
    budget: '入门价格带',
    mass: '大众价格带',
    mid: '中端价格带',
    premium: '高端价格带',
    unknown: '未知价格带',
  };
  return labels[raw] ?? displayValue(raw);
}

function warningCopy(warnings?: string[]) {
  if (!warnings?.length) return null;
  if (warnings.includes('history_days')) return '当前输入窗口不足，组合结构和价格带机会只能用于方向性诊断。';
  return `当前组合经营质量门禁需要复核：${warnings.map(fieldLabel).join('、')}`;
}

function categoryHealth(row?: PortfolioCategoryMix | null) {
  if (!row) return { label: '待选择', tone: 'queued', copy: '选择左侧类别后查看组合解释。' };
  if ((row.revenue_share ?? 0) >= 0.45) {
    return { label: '头部集中', tone: 'warning', copy: '成交额占比较高，需要检查是否依赖单一品类。' };
  }
  if ((row.view_to_purchase_rate ?? 0) < 0.01 && row.views > 0) {
    return { label: '转化偏弱', tone: 'danger', copy: '浏览量存在，但购买转化偏低，适合检查价格带或推荐入口。' };
  }
  return { label: '结构健康', tone: 'success', copy: '成交贡献和转化没有明显异常，可作为稳定经营类目。' };
}

function opportunityCopy(type?: string) {
  if (type === 'price_band_mix') return '检查这个类别的价格带是否过度偏向高端、低端或缺少中端承接。';
  if (type === 'concentration_risk') return '检查成交额是否集中在少数品类、品牌或商品，避免组合抗风险能力过弱。';
  if (type === 'traffic_conversion_gap') return '检查有流量但转化弱的类别，适合优化商品、价格或推荐入口。';
  if (type === 'portfolio_watch') return '保留观察，不直接行动，用于样本不足或信号不稳定的类别。';
  return '综合展示价格带结构、集中度风险、流量转化缺口和观察队列。';
}

function opportunityAction(type?: string) {
  if (type === 'price_band_mix') return '调整价格带';
  if (type === 'concentration_risk') return '分散集中度';
  if (type === 'traffic_conversion_gap') return '修复转化';
  if (type === 'portfolio_watch') return '继续观察';
  return '综合复核';
}

export function PortfolioPage() {
  const [selectedCategory, setSelectedCategory] = useState('');
  const [opportunityType, setOpportunityType] = useState('');
  const summary = usePortfolioSummary();
  const categories = usePortfolioCategories(80);
  const brands = usePortfolioBrands({ category: selectedCategory || undefined, limit: 80 });
  const allPriceBands = usePortfolioPriceBands();
  const priceBands = usePortfolioPriceBands({ category: selectedCategory || undefined });
  const products = usePortfolioProducts({ category: selectedCategory || undefined, limit: 80 });
  const concentration = usePortfolioConcentration();
  const opportunities = usePortfolioOpportunities({ type: opportunityType || undefined, confidence: 0.1, limit: 80 });
  const quality = usePortfolioQuality();
  const hasError =
    summary.isError ||
    categories.isError ||
    allPriceBands.isError ||
    brands.isError ||
    priceBands.isError ||
    products.isError ||
    concentration.isError ||
    opportunities.isError ||
    quality.isError;
  const matrix = useMemo(() => priceBandMatrix(allPriceBands.data ?? []), [allPriceBands.data]);
  const warning = warningCopy(summary.data?.warnings ?? quality.data?.warnings);
  const topCategory = summary.data?.top_category;
  const categoryRows = categories.data ?? [];
  const selectedCategoryRow =
    categoryRows.find((row) => row.category_level1 === selectedCategory) ??
    topCategory ??
    categoryRows[0] ??
    null;
  const activeCategory = selectedCategoryRow?.category_level1 ?? '';
  const selectedHealth = categoryHealth(selectedCategoryRow);
  const selectedPriceBands = (allPriceBands.data ?? []).filter((row) => row.category_level1 === activeCategory);
  const maxCategoryRevenueShare = Math.max(...categoryRows.map((row) => row.revenue_share ?? 0), 0.001);
  const maxBandRevenue = Math.max(...selectedPriceBands.map((row) => row.revenue), 1);
  const opportunityRows = opportunities.data ?? [];
  const selectedCategoryOpportunityCount = opportunityRows.filter((row) => row.entity_id === activeCategory).length;
  const topOpportunity = opportunityRows.find((row) => row.entity_id === activeCategory) ?? opportunityRows[0];

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">品类与价格带组合智能</span>
        <h1>品类价格带组合经营分析</h1>
        <p>从真实行为、购买和价格字段评估品类、品牌、商品与价格带结构，识别集中度风险和可复核的经营机会。</p>
      </section>

      {hasError ? <div className="error-banner">组合经营缓存尚未完整生成，请先运行 Spark 刷新任务。</div> : null}
      {warning ? <div className="error-banner">{warning}</div> : null}

      <section className="ops-command-band">
        <div>
          <span className={`status-pill tone-${statusTone(summary.data?.quality_status)}`}>
            {statusLabel(summary.data?.quality_status)}
          </span>
          <h2>组合经营契约 v1</h2>
          <p>{summary.data?.recommended_action ? algorithmCopy(summary.data.recommended_action) : '等待组合经营分析报告'}</p>
        </div>
        <Boxes size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>组合成交额</span>
          <strong>{money(summary.data?.total_revenue)}</strong>
          <small>{number(summary.data?.total_purchases)} 次购买</small>
        </article>
        <article className="metric-card">
          <span>头部品类</span>
          <strong>{topCategory ? displayValue(topCategory.category_level1) : '待生成'}</strong>
          <small>{percent(topCategory?.revenue_share)} 成交额占比</small>
        </article>
        <article className="metric-card tone-warning">
          <span>商品集中度</span>
          <strong>{score(summary.data?.product_revenue_hhi)}</strong>
          <small>头部商品占比 {percent(summary.data?.top_product_revenue_share)}</small>
        </article>
        <article className="metric-card">
          <span>机会队列</span>
          <strong>{number(summary.data?.opportunity_count)}</strong>
          <small>{number(summary.data?.price_band_count)} 个价格带</small>
        </article>
      </section>

      <section className="portfolio-workbench" aria-label="组合经营类别覆盖工作台">
        <div className="portfolio-workbench-head">
          <div>
            <span className="eyebrow">Category Coverage Matrix</span>
            <h2>每个品类都有入口，点击后联动价格带、品牌和机会解释</h2>
            <p>这里展示的是品类级摘要，不把所有明细铺满页面；卡片越长表示成交额占比越高，状态表示当前经营风险。</p>
          </div>
          <label htmlFor="portfolio-opportunity-lens" className="portfolio-lens-select">
            <span><Target size={15} /> 机会视角</span>
            <select id="portfolio-opportunity-lens" value={opportunityType} onChange={(event) => setOpportunityType(event.target.value)}>
              <option value="">全部机会</option>
              <option value="price_band_mix">价格带结构</option>
              <option value="concentration_risk">集中度风险</option>
              <option value="traffic_conversion_gap">流量转化缺口</option>
              <option value="portfolio_watch">观察队列</option>
            </select>
          </label>
        </div>

        <div className="portfolio-workbench-grid">
          <article className="portfolio-category-matrix" aria-label="品类覆盖矩阵">
            <div className="panel-title">
              <div>
                <h2>类别覆盖矩阵</h2>
                <p>覆盖当前缓存中的所有品类，点击类别查看右侧解释。</p>
              </div>
              <Layers3 size={20} />
            </div>
            <div className="portfolio-category-grid">
              <button
                type="button"
                className={!selectedCategory ? 'is-active' : ''}
                onClick={() => setSelectedCategory('')}
              >
                <span>全部品类</span>
                <strong>{number(summary.data?.category_count)}</strong>
                <small>查看全局组合结构</small>
                <i style={{ width: '100%' }} />
              </button>
              {categoryRows.map((row) => {
                const health = categoryHealth(row);
                const width = `${Math.max(6, ((row.revenue_share ?? 0) / maxCategoryRevenueShare) * 100)}%`;
                return (
                  <button
                    type="button"
                    className={`${selectedCategory === row.category_level1 ? 'is-active' : ''} tone-${health.tone}`}
                    key={row.category_level1}
                    onClick={() => setSelectedCategory(row.category_level1)}
                  >
                    <span>{displayValue(row.category_level1)}</span>
                    <strong>{percent(row.revenue_share)}</strong>
                    <small>{number(row.purchases)} 次购买 · {percent(row.view_to_purchase_rate)} 转化</small>
                    <i style={{ width }} />
                  </button>
                );
              })}
            </div>
          </article>

          <aside className="portfolio-category-explainer" aria-label="选中品类经营解释器">
            <div className="panel-title">
              <div>
                <h2>{activeCategory ? `${displayValue(activeCategory)} 经营解释器` : '全局经营解释器'}</h2>
                <p>把品类、价格带和机会队列翻译成可复核动作。</p>
              </div>
              <Gauge size={20} />
            </div>
            <div className={`portfolio-health-card tone-${selectedHealth.tone}`}>
              <span>{selectedHealth.label}</span>
              <strong>{money(selectedCategoryRow?.revenue)}</strong>
              <small>{selectedHealth.copy}</small>
            </div>
            <dl className="portfolio-explainer-grid">
              <div>
                <dt>成交额占比</dt>
                <dd>{percent(selectedCategoryRow?.revenue_share)}</dd>
              </div>
              <div>
                <dt>购买占比</dt>
                <dd>{percent(selectedCategoryRow?.purchase_share)}</dd>
              </div>
              <div>
                <dt>平均价格</dt>
                <dd>{money(selectedCategoryRow?.avg_price)}</dd>
              </div>
              <div>
                <dt>浏览到购买</dt>
                <dd>{percent(selectedCategoryRow?.view_to_purchase_rate)}</dd>
              </div>
            </dl>
            <div className="portfolio-lens-note">
              <span>{opportunityAction(opportunityType)}</span>
              <p>{opportunityCopy(opportunityType)}</p>
              <strong>{selectedCategoryOpportunityCount ? `${selectedCategoryOpportunityCount} 条命中当前品类` : '当前品类暂无直接命中，查看全局机会'}</strong>
            </div>
          </aside>
        </div>

        <div className="portfolio-band-strip" aria-label="选中品类价格带分布">
          <div className="panel-title">
            <div>
              <h2>价格带分布</h2>
              <p>{activeCategory ? `${displayValue(activeCategory)} 的价格带成交结构。` : '先选择一个品类查看价格带结构。'}</p>
            </div>
            <Tags size={20} />
          </div>
          <div className="portfolio-band-grid">
            {selectedPriceBands.length ? selectedPriceBands.map((band) => (
              <article key={`${band.category_level1}-${band.price_band}`}>
                <span>{priceBandLabel(band.price_band)}</span>
                <strong>{money(band.revenue)}</strong>
                <small>{number(band.purchases)} 次购买 · {percent(band.revenue_share)} 全局占比</small>
                <i style={{ width: `${Math.max(8, (band.revenue / maxBandRevenue) * 100)}%` }} />
              </article>
            )) : (
              <article>
                <span>等待价格带</span>
                <strong>待生成</strong>
                <small>选择左侧品类或运行 Spark 刷新。</small>
                <i style={{ width: '8%' }} />
              </article>
            )}
          </div>
        </div>

        <div className="portfolio-opportunity-rail" aria-label="组合经营机会摘要">
          <PackageSearch size={18} />
          <span>当前机会</span>
          <strong>{topOpportunity ? `${displayValue(topOpportunity.entity_id)} · ${label('action', topOpportunity.opportunity_type)}` : '待生成'}</strong>
          <small>{topOpportunity ? `${priceBandLabel(topOpportunity.price_band ?? '全部')} · 影响分 ${score(topOpportunity.impact_score)} · ${listLabels('reason', topOpportunity.reason_codes)}` : '暂无机会证据'}</small>
        </div>
      </section>

      <section className="forecast-main-grid portfolio-equal-grid">
        <article className="data-panel ops-card portfolio-scroll-card">
          <div className="panel-title">
            <div>
              <h2>价格带矩阵</h2>
              <p>行是品类，列是价格带，单元格展示成交额占比和购买量。</p>
            </div>
            <Layers3 size={20} />
          </div>
          <div className="table-scroll">
            <table aria-label="价格带组合矩阵">
              <thead>
                <tr>
                  <th>品类</th>
                  {matrix.bands.map((band) => (
                    <th key={band}>{priceBandLabel(band)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.categories.map((category) => (
                  <tr key={category}>
                    <td>{displayValue(category)}</td>
                    {matrix.bands.map((band) => {
                      const cell = matrix.byKey.get(`${category}:${band}`);
                      return (
                        <td key={band} aria-label={`${displayValue(category)} ${priceBandLabel(band)}`}>
                          {cell ? (
                            <>
                              <strong>{percent(cell.revenue_share)}</strong>
                              <br />
                              <small>{number(cell.purchases)} 次购买</small>
                            </>
                          ) : (
                            <>
                              <strong>无数据</strong>
                              <br />
                              <small>无价格带购买记录</small>
                            </>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="data-panel ops-card portfolio-scroll-card">
          <div className="panel-title">
            <div>
              <h2>质量门禁</h2>
              <p>校验购买样本、历史窗口、价格覆盖和价格带数量。</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <div className="quality-checks">
            {(quality.data?.checks ?? []).map((check) => (
              <div className={`quality-check tone-${check.passed ? 'success' : 'danger'}`} key={check.name}>
                <span>{fieldLabel(check.name)}</span>
                <strong>{String(check.actual)} {check.operator} {String(check.expected)}</strong>
              </div>
            ))}
          </div>
          <dl>
            <dt>历史天数</dt>
            <dd>{number(quality.data?.history_days)}</dd>
            <dt>品类数</dt>
            <dd>{number(quality.data?.category_count)}</dd>
            <dt>品牌数</dt>
            <dd>{number(quality.data?.brand_count)}</dd>
          </dl>
        </article>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>品类结构</h2>
            <p>成交额、购买、浏览和转化贡献，用于判断组合健康度。</p>
          </div>
          <ChartNoAxesCombined size={20} />
        </div>
        <div className="table-scroll">
          <table aria-label="品类组合结构">
            <thead>
              <tr>
                <th>品类</th>
                <th>成交额</th>
                <th>成交额占比</th>
                <th>购买数</th>
                <th>浏览到购买</th>
                <th>平均价格</th>
              </tr>
            </thead>
            <tbody>
              {(categories.data ?? []).map((row) => (
                <tr key={row.category_level1}>
                  <td>{displayValue(row.category_level1)}</td>
                  <td>{money(row.revenue)}</td>
                  <td>{percent(row.revenue_share)}</td>
                  <td>{number(row.purchases)}</td>
                  <td>{percent(row.view_to_purchase_rate)}</td>
                  <td>{money(row.avg_price)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="forecast-main-grid portfolio-equal-grid">
        <article className="data-panel jobs-panel portfolio-scroll-card">
          <div className="panel-title">
            <div>
              <h2>品牌贡献</h2>
              <p>当前筛选品类下的品牌成交额与购买占比。</p>
            </div>
          </div>
          <div className="table-scroll">
            <table aria-label="品牌组合贡献">
              <thead>
                <tr>
                  <th>品牌</th>
                  <th>品类</th>
                  <th>成交额</th>
                  <th>占比</th>
                  <th>转化</th>
                </tr>
              </thead>
              <tbody>
                {(brands.data ?? []).map((row) => (
                  <tr key={`${row.category_level1}-${row.brand}`}>
                    <td>{displayValue(row.brand)}</td>
                    <td>{displayValue(row.category_level1)}</td>
                    <td>{money(row.revenue)}</td>
                    <td>{percent(row.revenue_share)}</td>
                    <td>{percent(row.view_to_purchase_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="data-panel jobs-panel portfolio-scroll-card">
          <div className="panel-title">
            <div>
              <h2>商品集中度</h2>
              <p>头部商品成交额占比和集中度指数贡献。</p>
            </div>
          </div>
          <div className="table-scroll">
            <table aria-label="商品集中度排行">
              <thead>
                <tr>
                  <th>排名</th>
                  <th>商品</th>
                  <th>成交额</th>
                  <th>占比</th>
                </tr>
              </thead>
              <tbody>
                {(products.data?.length ? products.data : concentration.data ?? []).slice(0, 12).map((row) => (
                  <tr key={`${row.rank}-${row.product_id}`}>
                    <td>{row.rank}</td>
                    <td>
                      <strong>{row.product_id}</strong>
                      <br />
                      <small>{displayValue(row.brand)} · {displayValue(row.category_level1)}</small>
                    </td>
                    <td>{money(row.revenue)}</td>
                    <td>{percent(row.revenue_share)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section className="data-panel jobs-panel portfolio-scroll-card portfolio-wide-scroll">
        <div className="panel-title">
          <div>
            <h2>组合机会队列</h2>
            <p>一行代表一个品类对象在某个价格带或全局维度上的机会信号；同一品类可以命中多个价格带。</p>
          </div>
        </div>
        <div className="table-scroll">
          <table aria-label="组合经营机会队列">
            <thead>
              <tr>
                <th>类型</th>
                <th>品类对象</th>
                <th>触发价格带</th>
                <th>影响分</th>
                <th>置信度</th>
                <th>证据</th>
              </tr>
            </thead>
            <tbody>
              {(opportunities.data ?? []).map((row) => (
                <tr key={`${row.opportunity_type}-${row.entity_id}-${row.price_band ?? 'all'}`}>
                  <td>{label('action', row.opportunity_type)}</td>
                  <td>{displayValue(row.entity_id)}</td>
                  <td>{row.price_band ? priceBandLabel(row.price_band) : '全部'}</td>
                  <td>{score(row.impact_score)}</td>
                  <td>{percent(row.confidence)}</td>
                  <td>{listLabels('reason', row.reason_codes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
