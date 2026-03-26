import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { I18nProvider } from '../i18n/I18nProvider'
import { useCerberusStore } from '../store'
import { ExecutionConsole } from './ExecutionConsole'

function makeResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'content-type': 'application/json',
    },
  })
}

describe('ExecutionConsole', () => {
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)

      if (url.includes('/api/v1/trading/policy')) {
        return makeResponse({
          policy: {
            enforced: true,
            binance_allowed_symbols: ['BTCUSDT'],
            alpaca_allowed_symbols: ['AAPL'],
            max_binance_order_qty: 2,
            max_binance_order_notional_usd: 100000,
          },
        })
      }

      if (url.includes('/api/v1/binance/symbol-rules')) {
        return makeResponse({
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
        return makeResponse({ account_number: 'demo' })
      }

      if (url.includes('/api/v1/binance/order/test') && init?.method === 'POST') {
        return makeResponse({
          accepted: true,
          order_id: 'binance-test-001',
          request_id: 'rid-binance-001',
        })
      }

      if (url.includes('/api/v1/alpaca/orders') && init?.method === 'POST') {
        return makeResponse({ id: 'alpaca-order-001', status: 'accepted' })
      }

      return makeResponse({ error: 'not mocked' }, 404)
    }) as typeof fetch
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('runs precheck then submits binance test order', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <I18nProvider>
          <ExecutionConsole selectedSymbol="BTCUSDT" latestBid="50000" latestAsk="50010" />
        </I18nProvider>
      </QueryClientProvider>,
    )

    const precheckButton = await screen.findByTestId('run-precheck-button')
    await userEvent.click(precheckButton)

    await waitFor(() => {
      const status = screen.getByTestId('binance-precheck-status')
      expect(status.textContent).toBeTruthy()
    })

    await userEvent.click(screen.getByTestId('submit-binance-order-button'))

    await waitFor(() => {
      expect(screen.getByTestId('binance-response').textContent).toContain('accepted')
    })

    const submitFlow = useCerberusStore.getState().uiState.core_flow.submit
    expect(submitFlow.state).toBe('success')
    expect(submitFlow.request_id).toBe('rid-binance-001')
  })
})
