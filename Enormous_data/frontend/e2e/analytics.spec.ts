import { expect, test, type Page } from '@playwright/test';

const envelope = <T>(data: T, message = 'ok') => ({
  code: 0,
  message,
  data,
  meta: { request_id: 'e2e-request-id' },
});

async function mockApi(page: Page) {
  await page.route('**/api/v1/summary', (route) =>
    route.fulfill({
      json: envelope({
        raw_rows: 1000,
        cleaned_rows: 960,
        removed_rows: 40,
        duplicate_rows: 12,
        invalid_price_rows: 8,
        missing_brand_rows: 20,
        unique_users: 320,
        unique_sessions: 480,
        total_sales: 58230.5,
      }),
    }),
  );
  await page.route('**/api/v1/events/distribution', (route) =>
    route.fulfill({ json: envelope([{ name: 'view', value: 720 }, { name: 'purchase', value: 80 }]) }),
  );
  await page.route('**/api/v1/trend/daily-events', (route) =>
    route.fulfill({ json: envelope([{ date: '2020-01-01', value: 400 }, { date: '2020-01-02', value: 560 }]) }),
  );
  await page.route('**/api/v1/trend/daily-sales', (route) =>
    route.fulfill({ json: envelope([{ date: '2020-01-01', value: 18230.5 }, { date: '2020-01-02', value: 40000 }]) }),
  );
  await page.route('**/api/v1/ranking/categories', (route) =>
    route.fulfill({ json: envelope([{ name: 'electronics.smartphone', value: 300 }, { name: 'apparel.shoes', value: 220 }]) }),
  );
  await page.route('**/api/v1/ranking/brands', (route) =>
    route.fulfill({ json: envelope([{ name: 'apple', value: 200 }, { name: 'nike', value: 120 }]) }),
  );
  await page.route('**/api/v1/job', (route) =>
    route.fulfill({
      json: envelope({
        status: 'success',
        started_at: '2020-01-01T00:00:00',
        finished_at: '2020-01-01T00:01:00',
        message: '缓存已生成',
        input_path: 'data/sample/ecommerce_events.csv',
      }),
    }),
  );
  await page.route('**/api/v1/refresh', (route) => route.fulfill({ status: 202, json: envelope({ status: 'running' }, 'refresh started') }));
  await page.route('**/api/v1/table**', (route) => {
    const url = new URL(route.request().url());
    const eventType = url.searchParams.get('event_type');
    const rows = [
      {
        event_time: '2020-01-01 00:00:00 UTC',
        event_type: 'view',
        product_id: '1001',
        category_id: '2001',
        category_code: 'electronics.smartphone',
        brand: 'apple',
        price: '999.9',
        user_id: '501',
        user_session: 's-1',
      },
      {
        event_time: '2020-01-01 00:02:00 UTC',
        event_type: 'purchase',
        product_id: '1002',
        category_id: '2002',
        category_code: 'apparel.shoes',
        brand: 'nike',
        price: '299.9',
        user_id: '502',
        user_session: 's-2',
      },
    ].filter((row) => !eventType || row.event_type === eventType);
    route.fulfill({ json: envelope({ page: 1, size: 10, total: rows.length, rows }) });
  });
}

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test('dashboard renders summary cards and charts', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: '电商用户行为大数据分析工作台' })).toBeVisible();
  await expect(page.getByText('有效事件')).toBeVisible();
  await expect(page.getByText('行为类型分布')).toBeVisible();
  await expect(page.locator('canvas')).toHaveCount(4);
});

test('table supports event filtering', async ({ page }) => {
  await page.goto('/table');

  await expect(page.getByText('electronics.smartphone')).toBeVisible();
  await page.getByRole('combobox').selectOption('purchase');
  await expect(page.getByText('apparel.shoes')).toBeVisible();
  await expect(page.getByText('electronics.smartphone')).toHaveCount(0);
  await expect(page.getByText('第 1 页')).toBeVisible();
});

test('ops page triggers refresh workflow', async ({ page }) => {
  await page.goto('/ops');

  await expect(page.getByText('Spark 作业状态')).toBeVisible();
  await page.getByRole('button', { name: '刷新' }).click();
  await expect(page.getByText('缓存已生成')).toBeVisible();
});
