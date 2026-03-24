import type { StateCreator } from 'zustand'

import { toErrorMessage } from '../../lib/http'
import type { ExecutionTradingSlice, RootStore } from './shared'
import { normalizeOrderEvent } from './execution-trading/events'
import {
  loadBinanceRuleEnvelope,
  loadRecentOrderEventsEnvelope,
  loadTradingPolicyEnvelope,
} from './execution-trading/loaders'
import { connectOrdersSocket } from './execution-trading/socket'

const MAX_TIMELINE_EVENTS = 500

function markReady(get: () => RootStore): void {
  get().uiActions.setDomainStatus('execution-trading', {
    state: 'ready',
    stale: false,
    reason: undefined,
  })
}

function markLoading(get: () => RootStore): void {
  get().uiActions.setDomainStatus('execution-trading', {
    state: 'loading',
    stale: true,
    reason: undefined,
  })
}

function markDegraded(get: () => RootStore, reason: string): void {
  get().uiActions.setDomainStatus('execution-trading', {
    state: 'degraded',
    stale: true,
    reason,
  })
}

export const createExecutionTradingSlice: StateCreator<RootStore, [], [], ExecutionTradingSlice> = (
  set,
  get,
) => ({
  executionTrading: {
    latest_event: undefined,
    order_events: [],
    heartbeat: undefined,
    filter_symbol: 'ALL',
    filter_account_id: 'ALL',
    trading_policy: undefined,
    binance_rule: undefined,
  },
  executionTradingActions: {
    connectOrdersSocket: () => {
      const { env } = get()
      connectOrdersSocket({
        liveStreamEnabled: env.live_stream_enabled,
        wsBase: env.ws_base,
        onLoading: () => {
          markLoading(get)
        },
        onHeartbeat: (message) => {
          set((state) => ({
            executionTrading: {
              ...state.executionTrading,
              heartbeat: message,
            },
          }))
          markReady(get)
        },
        onEvent: (event) => {
          set((state) => ({
            executionTrading: {
              ...state.executionTrading,
              latest_event: event,
              heartbeat: undefined,
              order_events: [event, ...state.executionTrading.order_events].slice(0, MAX_TIMELINE_EVENTS),
            },
          }))
          markReady(get)
        },
        onDegraded: (reason) => {
          markDegraded(get, reason)
        },
      })
    },
    loadRecentOrderEvents: async () => {
      const { env } = get()
      const response = await loadRecentOrderEventsEnvelope(env.gateway_base)

      if (!response.ok || !response.payload) {
        markDegraded(get, toErrorMessage(response.error))
        return
      }

      const normalized = response.payload.events.map(normalizeOrderEvent)
      set((state) => ({
        executionTrading: {
          ...state.executionTrading,
          latest_event: normalized[0],
          order_events: normalized,
        },
      }))

      markReady(get)
    },
    loadTradingPolicy: async () => {
      const { env } = get()
      const response = await loadTradingPolicyEnvelope(env.gateway_base)

      if (!response.ok) {
        markDegraded(get, toErrorMessage(response.error))
        return
      }

      set((state) => ({
        executionTrading: {
          ...state.executionTrading,
          trading_policy: response.payload?.policy,
        },
      }))

      markReady(get)
    },
    loadBinanceRule: async (symbol) => {
      const { env } = get()
      const response = await loadBinanceRuleEnvelope(env.gateway_base, symbol)

      if (!response.ok) {
        markDegraded(get, toErrorMessage(response.error))
        return
      }

      set((state) => ({
        executionTrading: {
          ...state.executionTrading,
          binance_rule: response.payload?.rule,
        },
      }))

      markReady(get)
    },
    setFilters: (filters) => {
      set((state) => ({
        executionTrading: {
          ...state.executionTrading,
          filter_symbol: filters.symbol ?? state.executionTrading.filter_symbol,
          filter_account_id: filters.account_id ?? state.executionTrading.filter_account_id,
        },
      }))
    },
  },
})
