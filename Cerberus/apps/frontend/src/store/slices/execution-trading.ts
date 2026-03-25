import type { StateCreator } from 'zustand'

import { formatAppError, toAppError } from '../../lib/http'
import type { ExecutionTradingSlice, RootStore } from './shared'
import { normalizeOrderEvent } from './execution-trading/events'
import {
  loadBinanceRuleEnvelope,
  loadRecentOrderEventsEnvelope,
  loadTradingPolicyEnvelope,
} from './execution-trading/loaders'
import { connectOrdersSocket } from './execution-trading/socket'

const MAX_TIMELINE_EVENTS = 500

function readRequestId(payload: Record<string, unknown>): string | undefined {
  const direct = payload.request_id
  if (typeof direct === 'string' && direct.trim().length > 0) {
    return direct
  }
  const nested = (payload.error as { request_id?: unknown } | undefined)?.request_id
  if (typeof nested === 'string' && nested.trim().length > 0) {
    return nested
  }
  return undefined
}

function markReady(get: () => RootStore, requestId?: string): void {
  get().uiActions.setDomainStatus('execution-trading', {
    state: 'ready',
    stale: false,
    reason: undefined,
    request_id: requestId,
  })
}

function markLoading(get: () => RootStore): void {
  get().uiActions.setDomainStatus('execution-trading', {
    state: 'loading',
    stale: true,
    reason: undefined,
    request_id: undefined,
  })
}

function markDegraded(get: () => RootStore, reason: string, requestId?: string): void {
  get().uiActions.setDomainStatus('execution-trading', {
    state: 'degraded',
    stale: true,
    reason,
    request_id: requestId,
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
    filter_status: 'ALL',
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
          get().uiActions.setCoreFlowStep('feedback', {
            state: 'active',
            reason: message,
          })
          markReady(get)
        },
        onEvent: (event) => {
          const eventRequestId = readRequestId(event.payload)
          set((state) => ({
            executionTrading: {
              ...state.executionTrading,
              latest_event: event,
              heartbeat: undefined,
              order_events: [event, ...state.executionTrading.order_events].slice(0, MAX_TIMELINE_EVENTS),
            },
          }))
          get().uiActions.setCoreFlowStep('feedback', {
            state: 'success',
            reason: event.event_type,
            request_id: eventRequestId,
          })
          markReady(get, eventRequestId)
        },
        onDegraded: (reason) => {
          get().uiActions.setCoreFlowStep('feedback', {
            state: 'degraded',
            reason,
          })
          markDegraded(get, reason)
        },
      })
    },
    loadRecentOrderEvents: async (filters) => {
      const { env } = get()
      const currentFilters = get().executionTrading
      markLoading(get)
      const response = await loadRecentOrderEventsEnvelope(env.gateway_base, {
        symbol: filters?.symbol ?? currentFilters.filter_symbol,
        account_id: filters?.account_id ?? currentFilters.filter_account_id,
        order_id: filters?.order_id,
        status: filters?.status ?? currentFilters.filter_status,
        request_id: filters?.request_id,
      })

      if (!response.ok || !response.payload) {
        const error = toAppError(response.error, 'recent_order_events_failed')
        markDegraded(get, formatAppError(error), error.request_id)
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

      markReady(get, response.payload.request_id)
    },
    loadTradingPolicy: async () => {
      const { env } = get()
      const response = await loadTradingPolicyEnvelope(env.gateway_base)

      if (!response.ok) {
        const error = toAppError(response.error, 'trading_policy_failed')
        markDegraded(get, formatAppError(error), error.request_id)
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
        const error = toAppError(response.error, 'binance_rule_failed')
        markDegraded(get, formatAppError(error), error.request_id)
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
      const current = get().executionTrading
      const nextSymbol = filters.symbol ?? current.filter_symbol
      const nextAccountId = filters.account_id ?? current.filter_account_id
      const nextStatus = filters.status ?? current.filter_status

      set((state) => ({
        executionTrading: {
          ...state.executionTrading,
          filter_symbol: nextSymbol,
          filter_account_id: nextAccountId,
          filter_status: nextStatus,
        },
      }))

      void get().executionTradingActions.loadRecentOrderEvents({
        symbol: nextSymbol,
        account_id: nextAccountId,
        status: nextStatus,
      })
    },
  },
})
