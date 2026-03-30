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
        inference_catalog: undefined,
        inference_last_result: undefined,
        inference_pending_action: undefined,
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
            rollout: {
              configured_mode: 'primary',
              target_mode: 'primary',
              effective_mode: 'observe',
              override_active: false,
              auto_promote_enabled: true,
              force_primary: false,
              promotion_eligible: false,
              blockers: ['offline_macro_f1_below_threshold'],
              required_observe_ticks: 500,
              compared_ticks: 18,
              required_agreement_ratio: 0.55,
              agreement_ratio: 0.5,
              required_macro_f1: 0.58,
              current_macro_f1: 0.5001,
              started_at: '2026-03-30T00:00:00Z',
              last_transition_at: '2026-03-30T00:00:00Z',
            },
            comparison: {
              observed_ticks: 20,
              compared_ticks: 18,
              agreement_count: 9,
              divergence_count: 9,
              agreement_ratio: 0.5,
              rule_signal_counts: { BUY: 9, HOLD: 9 },
              inference_signal_counts: { SELL: 9, HOLD: 9 },
              symbols: [],
            },
            audit: [
              {
                event_type: 'rollout_holdback',
                created_at: '2026-03-30T00:00:00Z',
                message: 'primary rollout held back until promotion gates pass',
                metadata: {},
              },
            ],
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
    expect(state.inference_status?.rollout?.effective_mode).toBe('observe')
    expect(state.inference_status?.comparison?.compared_ticks).toBe(18)
    expect(state.inference_status?.active_model?.model_id).toBe('cerberus-transformer-lstm')
    expect(state.last_error).toBeUndefined()
  })
})
