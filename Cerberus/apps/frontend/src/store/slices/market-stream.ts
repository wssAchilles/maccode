import type { StateCreator } from 'zustand'

import { formatAppError, requestEnvelope, toAppError } from '../../lib/http'
import type { Candle, MarketMessage } from '../../types/contracts'
import type { MarketStreamSlice, RootStore } from './shared'

let marketSocket: WebSocket | null = null
let pendingMessages: MarketMessage[] = []
let flushHandle: number | null = null
let marketReconnectHandle: number | null = null
let marketReconnectAttempt = 0

const MAX_MARKET_RECONNECT_DELAY_MS = 30_000

function normalizeSymbol(input: string): string {
  return input.trim().toUpperCase()
}

function scheduleBatchFlush(set: Parameters<StateCreator<RootStore>>[0], get: () => RootStore) {
  if (flushHandle !== null || pendingMessages.length === 0) {
    return
  }

  const scheduler =
    typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function'
      ? window.requestAnimationFrame.bind(window)
      : (cb: FrameRequestCallback) => window.setTimeout(cb, 16)

  flushHandle = scheduler(() => {
    const batch = pendingMessages
    pendingMessages = []
    flushHandle = null

    set((state) => {
      const nextBySymbol = { ...state.marketStream.latest_by_symbol }
      let latest: MarketMessage | undefined = state.marketStream.latest

      for (const item of batch) {
        nextBySymbol[item.symbol] = item
        latest = item
      }

      return {
        marketStream: {
          ...state.marketStream,
          latest,
          latest_by_symbol: nextBySymbol,
        },
      }
    })

    get().uiActions.setDomainStatus('market-stream', {
      state: 'ready',
      stale: false,
      reason: undefined,
      request_id: undefined,
    })
  })
}

function clearMarketReconnectHandle(): void {
  if (marketReconnectHandle !== null) {
    window.clearTimeout(marketReconnectHandle)
    marketReconnectHandle = null
  }
}

function scheduleMarketReconnect(get: () => RootStore): void {
  if (marketSocket || marketReconnectHandle !== null) {
    return
  }
  const { env } = get()
  if (!env.live_stream_enabled) {
    return
  }

  const delayMs = Math.min(MAX_MARKET_RECONNECT_DELAY_MS, 1_000 * 2 ** Math.min(marketReconnectAttempt, 5))
  marketReconnectAttempt += 1
  marketReconnectHandle = window.setTimeout(() => {
    marketReconnectHandle = null
    get().marketStreamActions.connectMarketSocket()
  }, delayMs)

  get().uiActions.setDomainStatus('market-stream', {
    state: 'degraded',
    stale: true,
    reason: `market websocket closed, reconnect in ${Math.round(delayMs / 1_000)}s`,
    request_id: undefined,
  })
}

export const createMarketStreamSlice: StateCreator<RootStore, [], [], MarketStreamSlice> = (
  set,
  get,
) => ({
  marketStream: {
    selected_symbol: 'BTCUSDT',
    latest: undefined,
    latest_by_symbol: {},
    candles: [],
  },
  marketStreamActions: {
    setSelectedSymbol: (symbol) => {
      const normalized = normalizeSymbol(symbol)
      set((state) => ({
        marketStream: {
          ...state.marketStream,
          selected_symbol: normalized,
        },
      }))
    },
    connectMarketSocket: () => {
      const { env } = get()
      if (!env.live_stream_enabled || marketSocket) {
        return
      }
      clearMarketReconnectHandle()

      get().uiActions.setDomainStatus('market-stream', {
        state: 'loading',
        stale: true,
        reason: undefined,
        request_id: undefined,
      })

      marketSocket = new WebSocket(`${env.ws_base}/ws/market`)

      marketSocket.onopen = () => {
        marketReconnectAttempt = 0
        get().uiActions.setDomainStatus('market-stream', {
          state: 'ready',
          stale: false,
          reason: undefined,
          request_id: undefined,
        })
      }

      marketSocket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as MarketMessage
          if (!payload.symbol) {
            return
          }
          pendingMessages.push({
            ...payload,
            symbol: normalizeSymbol(payload.symbol),
          })
          scheduleBatchFlush(set, get)
        } catch {
          get().uiActions.setDomainStatus('market-stream', {
            state: 'degraded',
            stale: true,
            reason: 'invalid market payload',
            request_id: undefined,
          })
        }
      }

      marketSocket.onerror = () => {
        get().uiActions.setDomainStatus('market-stream', {
          state: 'degraded',
          stale: true,
          reason: 'market websocket error',
          request_id: undefined,
        })
      }

      marketSocket.onclose = () => {
        marketSocket = null
        scheduleMarketReconnect(get)
      }
    },
    loadCandles: async () => {
      const { env, marketStream } = get()
      const symbol = marketStream.selected_symbol

      get().uiActions.setDomainStatus('market-stream', {
        state: 'loading',
        stale: false,
        reason: undefined,
        request_id: undefined,
      })

      const response = await requestEnvelope<{ candles: Candle[] }>(
        `${env.gateway_base}/api/v1/klines?symbol=${encodeURIComponent(symbol)}&interval=1m&limit=200`,
      )

      if (!response.ok || !response.payload) {
        const error = toAppError(response.error, 'market_candles_failed')
        get().uiActions.setDomainStatus('market-stream', {
          state: 'error',
          stale: true,
          reason: formatAppError(error),
          request_id: error.request_id,
        })
        return
      }

      set((state) => ({
        marketStream: {
          ...state.marketStream,
          candles: response.payload?.candles ?? [],
        },
      }))

      get().uiActions.setDomainStatus('market-stream', {
        state: 'ready',
        stale: false,
        reason: undefined,
        request_id: undefined,
      })
    },
  },
})
