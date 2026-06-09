import { useTopBrands, useTopCategories } from '../api/hooks';
import { ChartPanel } from '../components/ChartPanel';
import { barOption } from '../lib/chartOptions';

export function RankingsPage() {
  const categories = useTopCategories();
  const brands = useTopBrands();

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">Ranking insight</span>
        <h1>品类与品牌排行洞察</h1>
        <p>用于观察业务集中度，后续可扩展为 drill-down 到表格明细。</p>
      </section>
      <section className="content-grid">
        <ChartPanel title="类目排行" subtitle="一级类目事件量 TopN" option={barOption(categories.data ?? [], '事件量', '#7cdaff')} />
        <ChartPanel title="品牌销售额排行" subtitle="purchase 销售额 TopN" option={barOption(brands.data ?? [], '销售额', '#a78bfa')} />
      </section>
    </>
  );
}
