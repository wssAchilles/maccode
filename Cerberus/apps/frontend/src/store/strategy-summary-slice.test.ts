import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useCerberusStore } from '.'

function makeResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'content-type': 'application/json',
    },
  })
}

describe('strategy summary slice', () => {
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    useCerberusStore.setState((state) => ({
      ...state,
      strategySummary: {
        signal: undefined,
        recent_signals: [],
        persistence_status: undefined,
        matching_orderbook: undefined,
        inference_status: undefined,
        last_error: undefined,
      },
    }))
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('hydrates inference_status from the aggregated strategy summary response', async () => {
    globalThis.fetch = vi.fn(async () =>
      makeResponse({
        request_id: 'rid-summary-frontend-001',
        strategy_base_url: 'https://strategy.example',
        symbol: 'BTCUSDT',
        source: 'auto',
        recent_limit: 8,
        orderbook_depth: 10,
        signal: { ok: true, status_code: 200, payload: { status: 'ready', signal: 'BUY', confidence: 0.91 } },
        recent_signals: { ok: true, status_code: 200, payload: { source: 'auto', count: 0, signals: [] } },
        persistence: {
          ok: true,
          status_code: 200,
          payload: {
            status: 'ok',
            worker: { processed_ticks: 12, has_last_signal: true },
            stores: { supabase_enabled: true, firebase_enabled: false },
          },
        },
        matching_orderbook: {
          ok: true,
          status_code: 200,
          payload: { enabled: true, symbol: 'BTCUSDT', depth: 10, bids: [], asks: [], generated_at_ms: 1 },
        },
        inference_status: {
          ok: true,
          status_code: 200,
          payload: {
            enabled: true,
            ready: true,
            engine: 'cerberus_signal_transformer_lstm',
            mode: 'observe',
            metadata: { lookback: 256 },
            active_model: {
              model_id: 'cerberus-transformer-lstm',
              version: 'v1',
              source: 'gcs',
              task: 'signal_inference',
              symbols: ['BTCUSDT', 'ETHUSDT'],
              metadata: { best_macro_f1: 0.5001, horizon: 32 },
            },
          },
        },
      }),
    ) as typeof fetch

    await useCerberusStore.getState().strategySummaryActions.refreshSummary()

    const state = useCerberusStore.getState().strategySummary
    expect(state.inference_status?.mode).toBe('observe')
    expect(state.inference_status?.active_model?.model_id).toBe('cerberus-transformer-lstm')
    expect(state.last_error).toBeUndefined()
  })
})
