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
  let fetchMock: ReturnType<typeof vi.fn>

  const EMPTY_FLOW = {
    state: 'idle' as const,
    last_update_ms: null,
    reason: undefined,
    request_id: undefined,
  }

  beforeEach(() => {
    useCerberusStore.setState((state) => ({
      ...state,
      uiState: {
        ...state.uiState,
        core_flow: {
          bootstrap: { ...EMPTY_FLOW },
          market: { ...EMPTY_FLOW },
          precheck: { ...EMPTY_FLOW },
          submit: { ...EMPTY_FLOW },
          feedback: { ...EMPTY_FLOW },
          cancel: { ...EMPTY_FLOW },
        },
      },
    }))

    fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
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
    })

    globalThis.fetch = fetchMock as typeof fetch
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
      expect(screen.getByRole('button', { name: /api response 200/i })).toBeTruthy()
    })

    await userEvent.click(screen.getByRole('button', { name: /api response 200/i }))

    await waitFor(() => {
      expect(screen.getByTestId('binance-response').textContent).toContain('accepted')
    })

    const submitFlow = useCerberusStore.getState().uiState.core_flow.submit
    expect(submitFlow.state).toBe('success')
    expect(submitFlow.request_id).toBe('rid-binance-001')

    const submitCall = fetchMock.mock.calls.find(
      ([url, init]) =>
        String(url).includes('/api/v1/binance/order/test') && init?.method === 'POST',
    )

    expect(submitCall).toBeTruthy()
    const headers = new Headers(submitCall?.[1]?.headers)
    expect(headers.has('idempotency-key')).toBe(false)
    expect(headers.has('x-idempotency-key')).toBe(false)
  })

  it('tracks market price updates until the operator edits the price manually', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    })

    const view = render(
      <QueryClientProvider client={queryClient}>
        <I18nProvider>
          <ExecutionConsole selectedSymbol="BTCUSDT" latestBid="50000" latestAsk="50010" />
        </I18nProvider>
      </QueryClientProvider>,
    )

    const priceInput = (await screen.findByTestId('binance-price-input')) as HTMLInputElement

    await waitFor(() => {
      expect(priceInput.value).toBe('50010')
    })

    view.rerender(
      <QueryClientProvider client={queryClient}>
        <I18nProvider>
          <ExecutionConsole selectedSymbol="BTCUSDT" latestBid="70005.2" latestAsk="70005.3" />
        </I18nProvider>
      </QueryClientProvider>,
    )

    await waitFor(() => {
      expect(priceInput.value).toBe('70005.3')
    })

    await userEvent.clear(priceInput)
    await userEvent.type(priceInput, '70006.1')

    view.rerender(
      <QueryClientProvider client={queryClient}>
        <I18nProvider>
          <ExecutionConsole selectedSymbol="BTCUSDT" latestBid="70008.4" latestAsk="70008.5" />
        </I18nProvider>
      </QueryClientProvider>,
    )

    await waitFor(() => {
      expect(priceInput.value).toBe('70006.1')
    })
  })
})
