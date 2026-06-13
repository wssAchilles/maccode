import { GitCompareArrows } from 'lucide-react';
import { useConversionDaily, useConversionFunnel, useProductConversion } from '../api/hooks';
import { ChartPanel } from '../components/ChartPanel';
import { displayValue } from '../i18n/displayText';
import { barOption, lineOption } from '../lib/chartOptions';
import type { DailyConversion, FunnelStep } from '../types/api';

function percent(value?: number) {
  return typeof value === 'number' ? `${(value * 100).toFixed(2)}%` : '待生成';
}

function money(value?: number) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : '待生成';
}

function compact(value?: number) {
  return typeof value === 'number' ? value.toLocaleString() : '待生成';
}

export function ConversionPage() {
  const funnel = useConversionFunnel();
  const daily = useConversionDaily();
  const products = useProductConversion(20);
  const totals = funnel.data?.totals;
  const hasError = funnel.isError || daily.isError || products.isError;
  const funnelRows = (funnel.data?.steps ?? []).map((step) => ({ name: step.step, value: step.sessions }));
  const dailyRateRows = (daily.data ?? []).map((row) => ({ date: row.date, value: Number((row.view_to_purchase_rate * 100).toFixed(3)) }));
  const weakestStep = (funnel.data?.steps ?? [])
    .filter((step) => step.step !== 'view')
    .reduce<FunnelStep | null>(
      (lowest, step) => (!lowest || step.rate_from_previous < lowest.rate_from_previous ? step : lowest),
      null,
    );
  const peakDailyRate = daily.data?.reduce<DailyConversion | null>(
    (best, row) => (!best || row.view_to_purchase_rate > best.view_to_purchase_rate ? row : best),
    null,
  );

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">转化智能分析</span>
        <h1>会话转化智能分析</h1>
        <p>基于真实 Kaggle 行为数据沉淀会话事实表，分析浏览、加购、购买的断点和商品转化效率。</p>
      </section>

      {hasError ? <div className="error-banner">转化缓存尚未生成，请先在作业状态页运行 Spark 刷新。</div> : null}

      <section className="metrics-strip">
        <article className="metric-card">
          <span>会话数</span>
          <strong>{compact(totals?.sessions)}</strong>
          <small>会话事实表行数</small>
        </article>
        <article className="metric-card tone-success">
          <span>浏览到加购</span>
          <strong>{percent(totals?.view_to_cart_rate)}</strong>
          <small>{compact(totals?.cart_sessions)} 个加购会话</small>
        </article>
        <article className="metric-card tone-warning">
          <span>加购到购买</span>
          <strong>{percent(totals?.cart_to_purchase_rate)}</strong>
          <small>{compact(totals?.purchase_sessions)} 个购买会话</small>
        </article>
        <article className="metric-card">
          <span>销售额</span>
          <strong>{money(totals?.revenue)}</strong>
          <small>客单价 {money(totals?.avg_order_value)}</small>
        </article>
      </section>

      <section className="content-grid">
        <ChartPanel
          title="会话漏斗"
          subtitle="正向路径会话数"
          option={barOption(funnelRows, '会话数', '#39d0c8', false)}
          summary={weakestStep ? `${displayValue(weakestStep.step, 'eventType')} 是当前最弱转化节点，前序转化率为 ${percent(weakestStep.rate_from_previous)}。` : '等待会话漏斗数据。'}
        />
        <ChartPanel
          title="每日购买转化率"
          subtitle="浏览到购买转化率"
          option={lineOption(dailyRateRows, '转化率', '#f59e0b')}
          summary={peakDailyRate ? `${peakDailyRate.date} 的购买转化率最高，为 ${percent(peakDailyRate.view_to_purchase_rate)}。` : '等待每日转化率数据。'}
        />
      </section>

      <section className="data-panel conversion-products-panel">
        <div className="panel-title">
          <div>
            <h2>商品转化效率</h2>
            <p>按销售额、购买数和浏览数排序的商品级转化表现。</p>
          </div>
          <GitCompareArrows size={20} />
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>商品</th>
                <th>品牌</th>
                <th>类目</th>
                <th>浏览</th>
                <th>加购</th>
                <th>购买</th>
                <th>浏览到加购</th>
                <th>加购到购买</th>
                <th>销售额</th>
              </tr>
            </thead>
            <tbody>
              {(products.data ?? []).map((row) => (
                <tr key={row.product_id}>
                  <td>{row.product_id}</td>
                  <td>{row.brand}</td>
                  <td>{row.category_level1}</td>
                  <td>{compact(row.views)}</td>
                  <td>{compact(row.carts)}</td>
                  <td>{compact(row.purchases)}</td>
                  <td>{percent(row.view_to_cart_rate)}</td>
                  <td>{percent(row.cart_to_purchase_rate)}</td>
                  <td>{money(row.revenue)}</td>
                </tr>
              ))}
              {products.data?.length === 0 ? (
                <tr>
                  <td colSpan={9}>等待商品转化缓存</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
