import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const url = request.url()
    const method = request.method()

    const json = (body: unknown, status = 200) =>
      route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify(body),
      })

    if (url.includes('/api/v1/klines')) {
      return json({
        candles: Array.from({ length: 20 }, (_, index) => {
          const ts = 1_710_000_000_000 + index * 60_000
          return [ts, '50000', '50100', '49900', '50050', '100']
        }),
      })
    }

    if (url.includes('/api/v1/strategy/summary')) {
      return json({
        request_id: 'req-summary-001',
        strategy_base_url: 'https://strategy.example.com',
        symbol: 'BTCUSDT',
        source: 'auto',
        recent_limit: 8,
        orderbook_depth: 10,
        signal: {
          ok: true,
          status_code: 200,
          url,
          payload: { status: 'ready', signal: 'BUY', confidence: 0.82, symbol: 'BTCUSDT' },
        },
        recent_signals: {
          ok: true,
          status_code: 200,
          url,
          payload: {
            source: 'supabase',
            count: 1,
            signals: [
              {
                strategy_id: 'mean-rev',
                symbol: 'BTCUSDT',
                signal: 'BUY',
                confidence: 0.82,
                created_at: new Date().toISOString(),
              },
            ],
          },
        },
        persistence: {
          ok: true,
          status_code: 200,
          url,
          payload: {
            status: 'ok',
            worker: {
              processed_ticks: 1234,
              has_last_signal: true,
            },
            stores: {
              supabase_enabled: true,
              firebase_enabled: true,
              supabase_table: 'signals',
              firebase_collection: 'signals',
            },
            matching: {
              health: {
                enabled: true,
                reachable: true,
                status: 'ok',
                service: 'matching',
                version: 'dev',
                uptime_seconds: 321,
              },
              stats: {
                enabled: true,
                live_orders: 4,
                trade_count: 88,
                tracked_orders: 5,
                rejected_orders: 1,
                symbols: 2,
              },
            },
          },
        },
        matching_orderbook: {
          ok: true,
          status_code: 200,
          url,
          payload: {
            enabled: true,
            symbol: 'BTCUSDT',
            depth: 10,
            bids: [{ price: 50000, total_quantity: 1.2, order_count: 3 }],
            asks: [{ price: 50010, total_quantity: 1.1, order_count: 2 }],
            generated_at_ms: Date.now(),
          },
        },
      })
    }

    if (url.includes('/api/v1/trading/policy')) {
      return json({
        policy: {
          enforced: true,
          binance_allowed_symbols: ['BTCUSDT'],
          alpaca_allowed_symbols: ['AAPL'],
          max_binance_order_qty: 5,
          max_binance_order_notional_usd: 500000,
          max_alpaca_order_qty: 50,
          max_alpaca_limit_notional_usd: 100000,
        },
      })
    }

    if (url.includes('/api/v1/binance/symbol-rules')) {
      return json({
        rule: {
          symbol: 'BTCUSDT',
          min_notional: 10,
          min_qty: 0.001,
          step_size: 0.001,
          tick_size: 0.1,
          refreshed_at: Date.now(),
        },
      })
    }

    if (url.includes('/api/v1/alpaca/account')) {
      return json({ account_number: 'paper-account', buying_power: '100000' })
    }

    if (url.includes('/api/v1/binance/order/test') && method === 'POST') {
      return json({ accepted: true, order_id: 'binance-demo-order' })
    }

    if (url.includes('/api/v1/alpaca/orders/') && url.includes('/cancel') && method === 'POST') {
      return json({ id: 'alpaca-demo-order', status: 'canceled' })
    }

    if (url.includes('/api/v1/alpaca/orders') && method === 'POST') {
      return json({ id: 'alpaca-demo-order', status: 'accepted' })
    }

    return json({ error: 'unhandled route' }, 404)
  })
})

test('core trading chain remains usable', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByTestId('app-shell')).toBeVisible()
  await expect(page.getByText(/Cerberus/)).toBeVisible()
  await page.goto('/?workspace=execution')
  await expect(page.getByTestId('app-shell')).toBeVisible()
  await expect(page.getByTestId('matching-orderbook-panel')).toBeVisible()
  await expect(page.getByTestId('execution-timeline-panel')).toBeVisible()

  await page.getByLabel('Quantity').fill('0.01')
  await page.getByLabel('Price').fill('50000')
  await page.getByTestId('run-precheck-button').click()
  await expect(page.getByTestId('binance-precheck-result')).toBeVisible()

  await page.getByTestId('submit-binance-order-button').click()
  await page.getByTestId('binance-response-drawer-trigger').click()
  await expect(page.getByTestId('binance-response-drawer-content')).toContainText('binance-demo-order')

  await page.getByRole('tab', { name: 'Alpaca' }).click()
  await page.getByTestId('submit-alpaca-order-button').click()
  await page.getByTestId('cancel-alpaca-order-button').click()
  await page.getByTestId('alpaca-response-drawer-trigger').click()
  await expect(page.getByTestId('alpaca-response-drawer-content')).toContainText('canceled')
})
