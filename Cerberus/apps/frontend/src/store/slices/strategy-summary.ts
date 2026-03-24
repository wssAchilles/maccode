import type { StateCreator } from 'zustand'

import { requestEnvelope, toErrorMessage } from '../../lib/http'
import type { StrategySummaryResponse } from '../../types/contracts'
import type { RootStore, StrategySummarySlice } from './shared'

function resolveSummaryErrors(summary: StrategySummaryResponse): string[] {
  return [
    summary.signal.ok ? null : `signal(${summary.signal.status_code})`,
    summary.recent_signals.ok ? null : `recent_signals(${summary.recent_signals.status_code})`,
    summary.persistence.ok ? null : `persistence(${summary.persistence.status_code})`,
    summary.matching_orderbook.ok
      ? null
      : `matching_orderbook(${summary.matching_orderbook.status_code})`,
  ].filter((value): value is string => Boolean(value))
}

export const createStrategySummarySlice: StateCreator<RootStore, [], [], StrategySummarySlice> = (
  set,
  get,
) => ({
  strategySummary: {
    signal: undefined,
    recent_signals: [],
    persistence_status: undefined,
    matching_orderbook: undefined,
    last_error: undefined,
  },
  strategySummaryActions: {
    refreshSummary: async () => {
      const { env, marketStream } = get()
      const symbol = marketStream.selected_symbol

      get().uiActions.setDomainStatus('strategy-summary', {
        state: 'loading',
        stale: false,
        reason: undefined,
      })

      const response = await requestEnvelope<StrategySummaryResponse>(
        `${env.gateway_base}/api/v1/strategy/summary?symbol=${encodeURIComponent(
          symbol,
        )}&recent_limit=8&source=auto&orderbook_depth=10`,
      )

      if (!response.ok || !response.payload) {
        const message = toErrorMessage(response.error)
        set((state) => ({
          strategySummary: {
            ...state.strategySummary,
            last_error: message,
          },
        }))
        get().uiActions.setDomainStatus('strategy-summary', {
          state: 'error',
          stale: true,
          reason: message,
        })
        return
      }

      const summary = response.payload
      const errors = resolveSummaryErrors(summary)
      const status = errors.length > 0 ? 'degraded' : 'ready'

      set((state) => ({
        strategySummary: {
          ...state.strategySummary,
          signal: summary.signal.ok ? summary.signal.payload : undefined,
          recent_signals: summary.recent_signals.ok
            ? summary.recent_signals.payload?.signals ?? []
            : [],
          persistence_status: summary.persistence.ok ? summary.persistence.payload : undefined,
          matching_orderbook: summary.matching_orderbook.ok
            ? summary.matching_orderbook.payload
            : undefined,
          last_error: errors.length > 0 ? `partial upstream failure: ${errors.join(', ')}` : undefined,
        },
      }))

      get().uiActions.setDomainStatus('strategy-summary', {
        state: status,
        stale: false,
        reason: errors.length > 0 ? errors.join(', ') : undefined,
      })
    },
  },
})
