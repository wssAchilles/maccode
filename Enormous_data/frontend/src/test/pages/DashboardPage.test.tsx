import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useEffect } from 'react';
import { describe, expect, it } from 'vitest';
import { DashboardPage } from '../../pages/DashboardPage';
import { ChartFilterProvider, useChartFilter } from '../../context/ChartFilterContext';
import { renderWithProviders } from '../render';

function renderDashboard() {
  return renderWithProviders(
    <ChartFilterProvider>
      <DashboardPage />
    </ChartFilterProvider>,
  );
}

function renderDashboardAt(route: string) {
  return renderWithProviders(
    <ChartFilterProvider>
      <DashboardPage />
    </ChartFilterProvider>,
    { route },
  );
}

function DashboardWithBrandFilter() {
  const { setFilter } = useChartFilter();

  useEffect(() => {
    setFilter({ field: 'brand', value: 'nike', label: '品牌：nike', sourceChartId: 'table-filter', sourceLabel: '明细查询' });
  }, [setFilter]);

  return <DashboardPage />;
}

describe('DashboardPage', () => {
  it('renders a compact chart-first dashboard without the old hero', async () => {
    renderDashboard();

    expect(await screen.findByText('电商行为分析驾驶舱')).toBeInTheDocument();
    expect(await screen.findByLabelText('驾驶舱运行状态')).toBeInTheDocument();
    expect(await screen.findByText('成交额主趋势')).toBeInTheDocument();
    expect(await screen.findByText('行为类型分布')).toBeInTheDocument();
    expect(await screen.findByText('智能门禁矩阵')).toBeInTheDocument();
    expect(await screen.findByLabelText('成交额主趋势图表标注')).toBeInTheDocument();
    expect(screen.queryByText('Kaggle 公开电商行为数据集')).not.toBeInTheDocument();
  });

  it('supports keyboard-equivalent chart filtering chips', async () => {
    const user = userEvent.setup();
    renderDashboard();

    await user.click(await screen.findByRole('button', { name: /行为：购买/ }));

    expect(await screen.findByLabelText('当前图表筛选')).toBeInTheDocument();
    expect((await screen.findAllByText('行为：购买')).length).toBeGreaterThan(1);
    expect((await screen.findAllByText(/已按 行为：购买 重新计算 3 张图/)).length).toBeGreaterThan(0);
    expect(await screen.findByText(/影响范围：图表高亮、组合明细、下钻路径/)).toBeInTheDocument();
    expect((await screen.findAllByText(/聚合图保留全量口径/)).length).toBeGreaterThan(0);
    expect(await screen.findByLabelText('下钻路径')).toHaveTextContent('总览行为：购买明细');
    const evidenceToggles = await screen.findAllByText('查看筛选证据');
    expect(evidenceToggles.length).toBeGreaterThan(0);
    await user.click(evidenceToggles[0]);
    expect((await screen.findAllByText('筛选样本')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('样本覆盖')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('物化层命中')).length).toBeGreaterThan(0);
    expect((await screen.findAllByLabelText('指标口径')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('事件量')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('运行批次：slice-run-1')).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('link', { name: '查看组合明细' })[0]).toHaveAttribute(
      'href',
      '/table?event_type=purchase&source=dashboard&sourceChart=dashboard-event-structure',
    );

    await user.click(await screen.findByRole('button', { name: '清除全部' }));

    expect(screen.queryByLabelText('当前图表筛选')).not.toBeInTheDocument();
  });

  it('restores dashboard filters from a shareable URL', async () => {
    renderDashboardAt('/?event_type=purchase&source=dashboard&sourceChart=dashboard-event-structure');

    expect(await screen.findByLabelText('当前图表筛选')).toHaveTextContent('行为：购买');
    expect(await screen.findByLabelText('当前图表筛选')).toHaveTextContent('来自：行为类型分布');
    expect(screen.getAllByRole('link', { name: '查看组合明细' })[0]).toHaveAttribute(
      'href',
      '/table?event_type=purchase&source=dashboard&sourceChart=dashboard-event-structure',
    );
  });

  it('keeps smart query as the filter source when restored on dashboard', async () => {
    renderDashboardAt('/?category_level1=electronics&source=query&sourceChart=controlled-query-result');

    expect(await screen.findByLabelText('当前图表筛选')).toHaveTextContent('类目：electronics');
    expect(await screen.findByLabelText('当前图表筛选')).toHaveTextContent('来自：智能查询结果');
    expect(screen.getAllByRole('link', { name: '查看组合明细' })[0]).toHaveAttribute(
      'href',
      '/table?category_level1=electronics&source=query&sourceChart=controlled-query-result',
    );
  });

  it('passes category filters into the drillthrough URL', async () => {
    const user = userEvent.setup();
    renderDashboard();

    await user.click(await screen.findByRole('button', { name: /类目：electronics/ }));

    expect(await screen.findByLabelText('当前图表筛选')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: '查看组合明细' })[0]).toHaveAttribute(
      'href',
      '/table?category_level1=electronics&source=dashboard&sourceChart=dashboard-category-ranking',
    );
  });

  it('keeps brand filters in the shareable drillthrough URL', async () => {
    renderWithProviders(
      <ChartFilterProvider>
        <DashboardWithBrandFilter />
      </ChartFilterProvider>,
    );

    expect(await screen.findByLabelText('当前图表筛选')).toHaveTextContent('品牌：nike');
    expect(await screen.findByLabelText('当前图表筛选')).toHaveTextContent('来自：明细查询');
    expect(screen.getAllByRole('link', { name: '查看组合明细' })[0]).toHaveAttribute(
      'href',
      '/table?brand=nike&source=table&sourceChart=table-filter',
    );
  });
});
