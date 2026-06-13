import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useEffect } from 'react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../render';
import { TablePage } from '../../pages/TablePage';
import { ChartFilterProvider, useChartFilter } from '../../context/ChartFilterContext';

function renderTable(route = '/table') {
  return renderWithProviders(
    <ChartFilterProvider>
      <TablePage />
    </ChartFilterProvider>,
    { route },
  );
}

function TableWithContextFilter() {
  const { setFilter } = useChartFilter();

  useEffect(() => {
    setFilter({
      field: 'event_type',
      value: 'purchase',
      label: '行为：购买',
      sourceChartId: 'dashboard-event-structure',
    });
  }, [setFilter]);

  return <TablePage />;
}

describe('TablePage', () => {
  it('uses URL event type as a shareable drillthrough filter', async () => {
    renderTable('/table?event_type=purchase&source=dashboard&sourceChart=dashboard-event-structure');

    expect(await screen.findByLabelText('当前明细范围')).toHaveTextContent('行为：购买');
    expect(screen.getByLabelText('当前明细范围')).toHaveTextContent('首页图表筛选 · 行为类型分布');
    expect(screen.getByRole('combobox', { name: '行为类型' })).toHaveValue('purchase');
    expect(await screen.findByText('apparel.shoes')).toBeInTheDocument();
    expect(screen.queryByText('electronics.smartphone')).not.toBeInTheDocument();
    expect(screen.getByText(/首页趋势、漏斗和成交额仍为全量 Spark 聚合口径/)).toBeInTheDocument();
  });

  it('uses URL category and brand as combination drillthrough filters', async () => {
    renderTable('/table?event_type=purchase&category_level1=apparel&brand=nike&source=dashboard&sourceChart=dashboard-category-ranking');

    expect(await screen.findByLabelText('当前明细范围')).toHaveTextContent('行为：购买');
    expect(screen.getByLabelText('当前明细范围')).toHaveTextContent('类目：apparel');
    expect(screen.getByLabelText('当前明细范围')).toHaveTextContent('品牌：nike');
    expect(screen.getByLabelText('当前明细范围')).toHaveTextContent('首页图表筛选 · 类目排行');
    expect(screen.getByRole('combobox', { name: '行为类型' })).toHaveValue('purchase');
    expect(screen.getByLabelText('一级类目')).toHaveValue('apparel');
    expect(screen.getByLabelText('品牌')).toHaveValue('nike');
    expect(await screen.findByText('apparel.shoes')).toBeInTheDocument();
    expect(screen.queryByText('electronics.smartphone')).not.toBeInTheDocument();
  });

  it('falls back to dashboard context when the URL has no event type', async () => {
    renderWithProviders(
      <ChartFilterProvider>
        <TableWithContextFilter />
      </ChartFilterProvider>,
      { route: '/table' },
    );

    expect(await screen.findByLabelText('当前明细范围')).toHaveTextContent('行为：购买');
    expect(screen.getByRole('combobox', { name: '行为类型' })).toHaveValue('purchase');
    expect(await screen.findByText('apparel.shoes')).toBeInTheDocument();
  });

  it('clears the drillthrough filter and returns to all events', async () => {
    const user = userEvent.setup();
    renderTable('/table?event_type=purchase&source=dashboard&sourceChart=dashboard-event-structure');

    expect(await screen.findByLabelText('当前明细范围')).toHaveTextContent('行为：购买');
    await user.click(screen.getByRole('button', { name: '清除全部筛选' }));

    expect(screen.getByLabelText('当前明细范围')).toHaveTextContent('全部行为');
    expect(screen.getByRole('combobox', { name: '行为类型' })).toHaveValue('');
    expect(await screen.findByText('electronics.smartphone')).toBeInTheDocument();
  });

  it('clears one combination filter without dropping the rest', async () => {
    const user = userEvent.setup();
    renderTable('/table?event_type=purchase&category_level1=apparel&brand=nike&source=dashboard&sourceChart=dashboard-category-ranking');

    expect(await screen.findByLabelText('当前明细范围')).toHaveTextContent('品牌：nike');
    await user.click(screen.getByRole('button', { name: '清除品牌：nike' }));

    expect(screen.getByLabelText('当前明细范围')).not.toHaveTextContent('品牌：nike');
    expect(screen.getByLabelText('当前明细范围')).toHaveTextContent('行为：购买');
    expect(screen.getByLabelText('当前明细范围')).toHaveTextContent('类目：apparel');
    expect(screen.getByLabelText('品牌')).toHaveValue('');
  });

  it('filters event type and resets to page one', async () => {
    const user = userEvent.setup();
    renderTable();

    await screen.findByText('electronics.smartphone');
    await user.click(screen.getByRole('button', { name: '下一页' }));
    expect(screen.getByText('第 2 页')).toBeInTheDocument();

    await user.selectOptions(screen.getByRole('combobox', { name: '行为类型' }), 'purchase');

    await waitFor(() => expect(screen.getByText('第 1 页')).toBeInTheDocument());
    expect(await screen.findByText('apparel.shoes')).toBeInTheDocument();
  });

  it('uses paginated table results from the API mock', async () => {
    const user = userEvent.setup();
    renderTable();

    await screen.findByText('electronics.smartphone');
    await user.click(screen.getByRole('button', { name: '下一页' }));

    expect(await screen.findByText('第 2 页')).toBeInTheDocument();
    expect(screen.getByText('共 12 条')).toBeInTheDocument();
  });

  it('changes page size and opens row inspection', async () => {
    const user = userEvent.setup();
    renderTable();

    await screen.findByText('electronics.smartphone');
    await user.selectOptions(screen.getByRole('combobox', { name: '每页行数' }), '25');
    await user.click(screen.getAllByRole('button', { name: '查看' })[0]);

    expect(await screen.findByLabelText('选中行为摘要')).toHaveTextContent('商品 ID 1002');
    expect(await screen.findByLabelText('选中行为摘要')).toHaveTextContent('一级类目 apparel');
    expect(await screen.findByLabelText('选中行为摘要')).toHaveTextContent('原始类目 apparel.shoes');
    expect(await screen.findByLabelText('选中行为摘要')).toHaveTextContent('品牌 nike');
  });
});
