import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../server';
import { api } from '../../lib/api';

describe('api client', () => {
  it('unwraps successful API envelopes', async () => {
    await expect(api.summary()).resolves.toMatchObject({ cleaned_rows: 960 });
  });

  it('throws backend messages for business errors', async () => {
    server.use(
      http.get('/api/v1/summary', () =>
        HttpResponse.json(
          { code: 50301, message: 'metric cache not found', data: null, meta: { request_id: 'req-error' } },
          { status: 503 },
        ),
      ),
    );

    await expect(api.summary()).rejects.toThrow('metric cache not found');
  });

  it('builds table query parameters', async () => {
    let requestedUrl = '';
    server.use(
      http.get('/api/v1/table', ({ request }) => {
        requestedUrl = request.url;
        return HttpResponse.json({
          code: 0,
          message: 'ok',
          data: { page: 2, size: 25, total: 0, source_dataset: 'cleaned_events', rows: [] },
          meta: {},
        });
      }),
    );

    await api.table({ page: 2, size: 25, event_type: 'purchase', category_level1: 'apparel', brand: 'nike' });

    const url = new URL(requestedUrl);
    expect(url.searchParams.get('page')).toBe('2');
    expect(url.searchParams.get('size')).toBe('25');
    expect(url.searchParams.get('event_type')).toBe('purchase');
    expect(url.searchParams.get('category_level1')).toBe('apparel');
    expect(url.searchParams.get('brand')).toBe('nike');
  });

  it('builds dashboard slice query parameters', async () => {
    let requestedUrl = '';
    server.use(
      http.get('/api/v1/dashboard/slice', ({ request }) => {
        requestedUrl = request.url;
        return HttpResponse.json({
          code: 0,
          message: 'ok',
          data: {
            summary: {
              event_count: 1,
              purchase_count: 1,
              total_sales: 199.9,
              unique_users: 1,
              unique_sessions: 1,
              avg_order_value: 199.9,
            },
            event_type_count: [{ name: 'purchase', value: 1 }],
            daily_events: [{ date: '2020-01-01', value: 1 }],
            daily_sales: [{ date: '2020-01-01', value: 199.9 }],
            top_categories: [{ name: 'apparel', value: 1 }],
            evidence: {
              source_dataset: 'cleaned_events',
              filtered_row_count: 1,
              total_row_count: 3,
              coverage_rate: 0.333333,
              query_ms: 4.2,
              run_id: 'run-1',
              contract_version: 'dashboard-slice/v1',
              dataset_version: 'run-1:dashboard-slice/v1',
              generated_at: '2026-06-11T08:28:42Z',
              filters: { event_type: 'purchase', category_level1: 'apparel', brand: 'nike' },
            },
          },
          meta: {},
        });
      }),
    );

    await api.dashboardSlice({ event_type: 'purchase', category_level1: 'apparel', brand: 'nike' });

    const url = new URL(requestedUrl);
    expect(url.searchParams.get('event_type')).toBe('purchase');
    expect(url.searchParams.get('category_level1')).toBe('apparel');
    expect(url.searchParams.get('brand')).toBe('nike');
  });

  it('posts controlled query text as JSON', async () => {
    let requestedBody: unknown = null;
    server.use(
      http.post('/api/v1/query/controlled', async ({ request }) => {
        requestedBody = await request.json();
        return HttpResponse.json({
          code: 0,
          message: 'ok',
          data: {
            contract_version: 'controlled-natural-query/v1',
            query: '按月份统计销售额',
            status: 'matched',
            matched: true,
            message: '已识别为受控查询，结果来自物化指标或缓存数据。',
            confidence: 0.92,
            intent: {
              metric: 'total_sales',
              metric_label: '成交额',
              dimension: 'month',
              dimension_label: '月份',
              aggregation: 'sum',
              chart_type: 'line',
              limit: 12,
              time_grain: 'month',
              event_type_filter: null,
              event_type_filter_label: null,
            },
            chart: {
              type: 'line',
              title: '按月份统计成交额',
              x_field: 'name',
              y_field: 'value',
              series_name: '成交额',
              dimension_label: '月份',
              metric_label: '成交额',
            },
            rows: [{ name: '2020-01', raw_name: '2020-01', value: 100, share: 1 }],
            suggestions: ['按月份统计销售额'],
            insight: '2020-01 的成交额最高，为 100。',
            evidence: {
              source_dataset: 'dashboard_metric_cube',
              run_id: 'query-run-1',
              contract_version: 'dashboard-metric-cube/v1',
              dataset_version: 'query-run-1:dashboard-metric-cube/v1',
              generated_at: '2026-06-11T08:28:42Z',
              query_ms: 4.2,
              row_count: 1,
              execution_engine: 'dashboard_slice_cache',
            },
          },
          meta: {},
        });
      }),
    );

    await expect(api.controlledQuery('按月份统计销售额')).resolves.toMatchObject({
      chart: { title: '按月份统计成交额' },
    });
    expect(requestedBody).toEqual({ query: '按月份统计销售额' });
  });

  it('reads pipeline governance endpoints', async () => {
    await expect(api.jobs(8)).resolves.toMatchObject({ total: 1 });
    await expect(api.jobLineage('job-1')).resolves.toMatchObject({
      input_snapshot: { file_count: 2 },
    });
    await expect(api.jobQuality('job-1')).resolves.toMatchObject({
      quality_status: 'passed',
    });
    await expect(api.opsEvidence()).resolves.toMatchObject({
      benchmark_summary: { yarn_only_to_algorithm_speedup: 1.801 },
    });
  });

  it('reads conversion intelligence endpoints', async () => {
    await expect(api.conversionFunnel()).resolves.toMatchObject({
      totals: { purchase_sessions: 3912 },
    });
    await expect(api.conversionDaily()).resolves.toHaveLength(3);
    await expect(api.productConversion(1)).resolves.toMatchObject([{ product_id: '1004856' }]);
  });

  it('reads merchandising optimization endpoints', async () => {
    await expect(api.optimizationSummary()).resolves.toMatchObject({
      solver_status: 'optimal',
    });
    await expect(api.optimizationPlan(1)).resolves.toMatchObject([{ action: 'feature_slot' }]);
    await expect(api.optimizationCandidates(1)).resolves.toMatchObject([{ confidence_weight: 0.82 }]);
    await expect(api.optimizationQuality()).resolves.toMatchObject({ budget_feasible: true });
  });

  it('reads revenue attribution endpoints', async () => {
    await expect(api.attributionSummary()).resolves.toMatchObject({
      contract_version: 'revenue-attribution/v1',
    });
    await expect(api.attributionModels()).resolves.toHaveLength(3);
    await expect(api.attributionEntities({ entity_type: 'category', model: 'time_decay', limit: 1 })).resolves.toMatchObject([
      { entity_id: 'electronics' },
    ]);
    await expect(api.attributionPaths(1)).resolves.toMatchObject([{ path_pattern: 'view>cart>purchase' }]);
    await expect(api.attributionAssists({ entity_type: 'category', limit: 1 })).resolves.toMatchObject([
      { suggested_action: 'monitor_assist_entity' },
    ]);
    await expect(api.attributionQuality()).resolves.toMatchObject({ quality_status: 'needs_review' });
  });
});
