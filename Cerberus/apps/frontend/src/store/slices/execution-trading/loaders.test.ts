import { afterEach, describe, expect, it, vi } from 'vitest'

import { loadRecentOrderEventsEnvelope } from './loaders'

describe('loadRecentOrderEventsEnvelope', () => {
  const originalFetch = globalThis.fetch

  afterEach(() => {
    globalThis.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('builds query params and skips ALL filters', async () => {
    const fetchMock = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          count: 0,
          events: [],
        }),
        {
          status: 200,
          headers: { 'content-type': 'application/json' },
        },
      )
    })
    globalThis.fetch = fetchMock as unknown as typeof fetch

    await loadRecentOrderEventsEnvelope('https://gateway.example.com', {
      symbol: 'BTCUSDT',
      account_id: 'ALL',
      status: 'submitted',
      request_id: 'rid-1',
    })

    const requestUrl = String(fetchMock.mock.calls[0]?.[0] ?? '')
    expect(requestUrl).toContain('/api/v1/orders/events/recent?')
    expect(requestUrl).toContain('limit=200')
    expect(requestUrl).toContain('symbol=BTCUSDT')
    expect(requestUrl).toContain('status=submitted')
    expect(requestUrl).toContain('request_id=rid-1')
    expect(requestUrl).not.toContain('account_id=')
  })
})
