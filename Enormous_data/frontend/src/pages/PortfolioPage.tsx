import { Boxes, ChartNoAxesCombined, Layers3, ShieldCheck } from 'lucide-react';
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
import type { PortfolioCategoryMix, PortfolioPriceBand } from '../types/api';

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : 'pending';
}

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : 'pending';
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : 'pending';
}

function score(value?: number | null) {
  return typeof value === 'number' ? value.toFixed(4) : 'pending';
}

function statusTone(status?: string) {
  if (status === 'passed' || status === 'low') return 'success';
  if (status === 'needs_review' || status === 'medium') return 'queued';
  return 'failed';
}

function categoryOptions(rows: PortfolioCategoryMix[]) {
  return Array.from(new Set(rows.map((row) => row.category_level1))).sort();
}

function priceBandMatrix(rows: PortfolioPriceBand[]) {
  const categories = Array.from(new Set(rows.map((row) => row.category_level1))).sort();
  const bands = Array.from(new Set(rows.map((row) => row.price_band))).sort();
  const byKey = new Map(rows.map((row) => [`${row.category_level1}:${row.price_band}`, row]));
  return { categories, bands, byKey };
}

function warningCopy(warnings?: string[]) {
  if (!warnings?.length) return null;
  if (warnings.includes('history_days')) return '当前输入窗口不足，组合结构和价格带机会只能用于方向性诊断。';
  return `当前组合经营质量门禁需要复核：${warnings.join(', ')}`;
}

export function PortfolioPage() {
  const [selectedCategory, setSelectedCategory] = useState('');
  const [opportunityType, setOpportunityType] = useState('');
  const summary = usePortfolioSummary();
  const categories = usePortfolioCategories(80);
  const brands = usePortfolioBrands({ category: selectedCategory || undefined, limit: 80 });
  const priceBands = usePortfolioPriceBands({ category: selectedCategory || undefined });
  const products = usePortfolioProducts({ category: selectedCategory || undefined, limit: 80 });
  const concentration = usePortfolioConcentration();
  const opportunities = usePortfolioOpportunities({ type: opportunityType || undefined, confidence: 0.1, limit: 80 });
  const quality = usePortfolioQuality();
  const hasError =
    summary.isError ||
    categories.isError ||
    brands.isError ||
    priceBands.isError ||
    products.isError ||
    concentration.isError ||
    opportunities.isError ||
    quality.isError;
  const options = useMemo(() => categoryOptions(categories.data ?? []), [categories.data]);
  const matrix = useMemo(() => priceBandMatrix(priceBands.data ?? []), [priceBands.data]);
  const warning = warningCopy(summary.data?.warnings ?? quality.data?.warnings);
  const topCategory = summary.data?.top_category;

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">Category & price-band portfolio intelligence</span>
        <h1>品类价格带组合经营分析</h1>
        <p>从真实行为、购买和价格字段评估品类、品牌、商品与价格带结构，识别集中度风险和可复核的经营机会。</p>
      </section>

      {hasError ? <div className="error-banner">组合经营缓存尚未完整生成，请先运行 Spark 刷新任务。</div> : null}
      {warning ? <div className="error-banner">{warning}</div> : null}

      <section className="ops-command-band">
        <div>
          <span className={`status-pill tone-${statusTone(summary.data?.quality_status)}`}>
            {summary.data?.quality_status ?? 'pending'}
          </span>
          <h2>{summary.data?.contract_version ?? 'portfolio-intelligence/v1'}</h2>
          <p>{summary.data?.recommended_action ?? '等待组合经营分析报告'}</p>
        </div>
        <Boxes size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>组合 GMV</span>
          <strong>{money(summary.data?.total_revenue)}</strong>
          <small>{number(summary.data?.total_purchases)} purchases</small>
        </article>
        <article className="metric-card">
          <span>Top 品类</span>
          <strong>{topCategory?.category_level1 ?? 'pending'}</strong>
          <small>{percent(topCategory?.revenue_share)} revenue share</small>
        </article>
        <article className="metric-card tone-warning">
          <span>商品集中度</span>
          <strong>{score(summary.data?.product_revenue_hhi)}</strong>
          <small>top product {percent(summary.data?.top_product_revenue_share)}</small>
        </article>
        <article className="metric-card">
          <span>机会队列</span>
          <strong>{number(summary.data?.opportunity_count)}</strong>
          <small>{number(summary.data?.price_band_count)} price bands</small>
        </article>
      </section>

      <section className="toolbar forecast-toolbar" aria-label="组合经营筛选">
        <label>
          <span>品类</span>
          <select value={selectedCategory} onChange={(event) => setSelectedCategory(event.target.value)}>
            <option value="">全部</option>
            {options.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>机会类型</span>
          <select value={opportunityType} onChange={(event) => setOpportunityType(event.target.value)}>
            <option value="">全部</option>
            <option value="price_band_mix">价格带结构</option>
            <option value="concentration_risk">集中度风险</option>
            <option value="traffic_conversion_gap">流量转化缺口</option>
            <option value="portfolio_watch">观察队列</option>
          </select>
        </label>
      </section>

      <section className="forecast-main-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>价格带矩阵</h2>
              <p>行是品类，列是价格带，单元格展示 GMV share 和购买量。</p>
            </div>
            <Layers3 size={20} />
          </div>
          <div className="table-scroll">
            <table aria-label="价格带组合矩阵">
              <thead>
                <tr>
                  <th>品类</th>
                  {matrix.bands.map((band) => (
                    <th key={band}>{band}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.categories.map((category) => (
                  <tr key={category}>
                    <td>{category}</td>
                    {matrix.bands.map((band) => {
                      const cell = matrix.byKey.get(`${category}:${band}`);
                      return (
                        <td key={band} aria-label={`${category} ${band}`}>
                          <strong>{percent(cell?.revenue_share)}</strong>
                          <br />
                          <small>{number(cell?.purchases)} purchases</small>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="data-panel ops-card">
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
                <span>{check.name}</span>
                <strong>{String(check.actual)} {check.operator} {String(check.expected)}</strong>
              </div>
            ))}
          </div>
          <dl>
            <dt>History days</dt>
            <dd>{number(quality.data?.history_days)}</dd>
            <dt>Categories</dt>
            <dd>{number(quality.data?.category_count)}</dd>
            <dt>Brands</dt>
            <dd>{number(quality.data?.brand_count)}</dd>
          </dl>
        </article>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>品类结构</h2>
            <p>GMV、购买、浏览和转化贡献，用于判断组合健康度。</p>
          </div>
          <ChartNoAxesCombined size={20} />
        </div>
        <div className="table-scroll">
          <table aria-label="品类组合结构">
            <thead>
              <tr>
                <th>品类</th>
                <th>GMV</th>
                <th>GMV Share</th>
                <th>Purchases</th>
                <th>View → Purchase</th>
                <th>Avg price</th>
              </tr>
            </thead>
            <tbody>
              {(categories.data ?? []).map((row) => (
                <tr key={row.category_level1}>
                  <td>{row.category_level1}</td>
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

      <section className="forecast-main-grid">
        <article className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>品牌贡献</h2>
              <p>当前筛选品类下的品牌 GMV 与购买占比。</p>
            </div>
          </div>
          <div className="table-scroll">
            <table aria-label="品牌组合贡献">
              <thead>
                <tr>
                  <th>品牌</th>
                  <th>品类</th>
                  <th>GMV</th>
                  <th>Share</th>
                  <th>转化</th>
                </tr>
              </thead>
              <tbody>
                {(brands.data ?? []).map((row) => (
                  <tr key={`${row.category_level1}-${row.brand}`}>
                    <td>{row.brand}</td>
                    <td>{row.category_level1}</td>
                    <td>{money(row.revenue)}</td>
                    <td>{percent(row.revenue_share)}</td>
                    <td>{percent(row.view_to_purchase_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>商品集中度</h2>
              <p>Top 商品 GMV share 和 HHI 贡献。</p>
            </div>
          </div>
          <div className="table-scroll">
            <table aria-label="商品集中度排行">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>商品</th>
                  <th>GMV</th>
                  <th>Share</th>
                </tr>
              </thead>
              <tbody>
                {(products.data?.length ? products.data : concentration.data ?? []).slice(0, 12).map((row) => (
                  <tr key={`${row.rank}-${row.product_id}`}>
                    <td>{row.rank}</td>
                    <td>
                      <strong>{row.product_id}</strong>
                      <br />
                      <small>{row.brand} · {row.category_level1}</small>
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

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>组合机会队列</h2>
            <p>所有建议只代表结构性优先级，不宣称因果效果。</p>
          </div>
        </div>
        <div className="table-scroll">
          <table aria-label="组合经营机会队列">
            <thead>
              <tr>
                <th>类型</th>
                <th>实体</th>
                <th>价格带</th>
                <th>Impact</th>
                <th>Confidence</th>
                <th>证据</th>
              </tr>
            </thead>
            <tbody>
              {(opportunities.data ?? []).map((row) => (
                <tr key={`${row.opportunity_type}-${row.entity_id}-${row.price_band ?? 'all'}`}>
                  <td>{row.opportunity_type}</td>
                  <td>{row.entity_id}</td>
                  <td>{row.price_band ?? 'all'}</td>
                  <td>{score(row.impact_score)}</td>
                  <td>{percent(row.confidence)}</td>
                  <td>{row.reason_codes.join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
