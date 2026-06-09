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
        return HttpResponse.json({ code: 0, message: 'ok', data: { page: 2, size: 25, total: 0, rows: [] }, meta: {} });
      }),
    );

    await api.table({ page: 2, size: 25, event_type: 'purchase' });

    const url = new URL(requestedUrl);
    expect(url.searchParams.get('page')).toBe('2');
    expect(url.searchParams.get('size')).toBe('25');
    expect(url.searchParams.get('event_type')).toBe('purchase');
  });

  it('reads pipeline governance endpoints', async () => {
    await expect(api.jobs(8)).resolves.toMatchObject({ total: 1 });
    await expect(api.jobLineage('job-1')).resolves.toMatchObject({
      input_snapshot: { file_count: 2 },
    });
    await expect(api.jobQuality('job-1')).resolves.toMatchObject({
      quality_status: 'passed',
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
