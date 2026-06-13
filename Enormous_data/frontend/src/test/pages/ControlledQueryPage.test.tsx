import { http, HttpResponse } from 'msw';
import userEvent from '@testing-library/user-event';
import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ChartFilterProvider, useChartFilter } from '../../context/ChartFilterContext';
import { controlledQueryFixture, envelope } from '../../mocks/fixtures';
import { ControlledQueryPage } from '../../pages/ControlledQueryPage';
import { renderWithProviders } from '../render';
import { server } from '../server';

function renderControlledQuery() {
  return renderWithProviders(
    <ChartFilterProvider>
      <ControlledQueryPage />
    </ChartFilterProvider>,
    { route: '/query' },
  );
}

function ContextProbe() {
  const { activeFilters } = useChartFilter();
  return <output aria-label="当前智能查询筛选">{activeFilters.map((filter) => filter.label).join('、') || '无筛选'}</output>;
}

describe('ControlledQueryPage', () => {
  it('renders Chinese controlled query result as a chart-first page', async () => {
    renderControlledQuery();

    expect(await screen.findByText('中文受控查询工作台')).toBeInTheDocument();
    expect(await screen.findByText('按月份统计成交额')).toBeInTheDocument();
    expect((await screen.findAllByText('成交额')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('月份')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('指标切片缓存')).length).toBeGreaterThan(0);
    expect(await screen.findByText('结果明细')).toBeInTheDocument();
    expect(screen.queryByText('total_sales')).not.toBeInTheDocument();
    expect(screen.queryByText('dashboard_slice_cache')).not.toBeInTheDocument();
  });

  it('uses suggestion chips as keyboard reachable query actions', async () => {
    const user = userEvent.setup();
    renderControlledQuery();

    await user.click(await screen.findByRole('button', { name: '按类目统计购买数' }));

    expect(await screen.findByDisplayValue('按类目统计购买数')).toBeInTheDocument();
    expect(await screen.findByText('按月份统计成交额')).toBeInTheDocument();
  });

  it('turns categorical query rows into dashboard and detail actions', async () => {
    const user = userEvent.setup();
    server.use(
      http.post('/api/v1/query/controlled', () =>
        HttpResponse.json(envelope({
          ...controlledQueryFixture,
          query: '按类目统计购买数',
          intent: {
            ...controlledQueryFixture.intent,
            metric: 'purchase_count',
            metric_label: '购买数',
            dimension: 'category_level1',
            dimension_label: '一级类目',
            aggregation: 'count',
            chart_type: 'bar',
            event_type_filter: 'purchase',
            event_type_filter_label: '购买',
          },
          chart: {
            ...controlledQueryFixture.chart,
            type: 'bar',
            title: '按类目统计购买数',
            series_name: '购买数',
            dimension_label: '一级类目',
            metric_label: '购买数',
          },
          rows: [
            { name: 'electronics', raw_name: 'electronics', value: 42, share: 0.6 },
            { name: 'apparel', raw_name: 'apparel', value: 28, share: 0.4 },
          ],
          insight: 'electronics 的购买数最高，为 42。',
        })),
      ),
    );

    renderWithProviders(
      <ChartFilterProvider>
        <ControlledQueryPage />
        <ContextProbe />
      </ChartFilterProvider>,
      { route: '/query' },
    );

    expect(await screen.findByText('按类目统计购买数')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '查看electronics明细' })).toHaveAttribute(
      'href',
      '/table?category_level1=electronics&source=query&sourceChart=controlled-query-result',
    );

    await user.click(screen.getByRole('button', { name: '应用electronics到驾驶舱' }));

    expect(await screen.findByLabelText('当前智能查询筛选')).toHaveTextContent('类目：electronics');
  });
});
