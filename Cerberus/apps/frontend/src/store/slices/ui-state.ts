import type { StateCreator } from 'zustand'

import type { Locale } from '../../i18n/messages'
import { DEFAULT_UI_STATE } from '../../types/contracts'
import type { RootStore, UIStateSlice } from './shared'

const LOCALE_KEY = 'cerberus.locale'

const STALE_THRESHOLD_MS = {
  'market-stream': 5_000,
  'strategy-summary': 12_000,
  'execution-trading': 15_000,
} as const

function resolveLocale(): Locale {
  if (typeof window === 'undefined') {
    return 'zh-CN'
  }

  const raw = window.localStorage.getItem(LOCALE_KEY)
  if (raw === 'zh-CN' || raw === 'en-US') {
    return raw
  }

  const browserLocale = window.navigator.language.toLowerCase()
  return browserLocale.startsWith('zh') ? 'zh-CN' : 'en-US'
}

const gatewayBase = import.meta.env.VITE_GATEWAY_BASE ?? 'http://localhost:8080'
const strategyBase = import.meta.env.VITE_STRATEGY_BASE ?? 'http://localhost:8001'
const wsBase = gatewayBase.startsWith('https')
  ? gatewayBase.replace(/^https/, 'wss')
  : gatewayBase.replace(/^http/, 'ws')
const liveStreamEnabled = import.meta.env.VITE_DISABLE_LIVE_STREAM !== 'true'

export const createUIStateSlice: StateCreator<RootStore, [], [], UIStateSlice> = (set, get) => ({
  env: {
    gateway_base: gatewayBase,
    strategy_base: strategyBase,
    ws_base: wsBase,
    live_stream_enabled: liveStreamEnabled,
  },
  uiState: {
    locale: resolveLocale(),
    live_announcement: '',
    domain_status: {
      'market-stream': { ...DEFAULT_UI_STATE },
      'strategy-summary': { ...DEFAULT_UI_STATE },
      'execution-trading': { ...DEFAULT_UI_STATE },
    },
  },
  uiActions: {
    setLocale: (locale) => {
      set((state) => ({
        uiState: {
          ...state.uiState,
          locale,
        },
      }))
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(LOCALE_KEY, locale)
      }
    },
    setDomainStatus: (domain, patch) => {
      set((state) => {
        const current = state.uiState.domain_status[domain]
        const next = {
          ...current,
          ...patch,
          last_update_ms: patch.last_update_ms ?? Date.now(),
          stale: patch.stale ?? false,
        }

        return {
          uiState: {
            ...state.uiState,
            domain_status: {
              ...state.uiState.domain_status,
              [domain]: next,
            },
          },
        }
      })
    },
    recomputeStaleFlags: (nowMs) => {
      const now = nowMs ?? Date.now()
      const current = get().uiState.domain_status

      set((state) => {
        const next = {
          'market-stream': { ...state.uiState.domain_status['market-stream'] },
          'strategy-summary': { ...state.uiState.domain_status['strategy-summary'] },
          'execution-trading': { ...state.uiState.domain_status['execution-trading'] },
        }

        ;(Object.keys(next) as Array<keyof typeof next>).forEach((domain) => {
          const previous = current[domain]
          const threshold = STALE_THRESHOLD_MS[domain]
          const stale =
            previous.last_update_ms === null ? true : now - previous.last_update_ms > threshold
          next[domain].stale = stale

          if (stale && next[domain].state === 'ready') {
            next[domain].state = 'degraded'
            next[domain].reason = 'stale data'
          }
        })

        return {
          uiState: {
            ...state.uiState,
            domain_status: next,
          },
        }
      })
    },
    announce: (message) => {
      set((state) => ({
        uiState: {
          ...state.uiState,
          live_announcement: message,
        },
      }))
    },
  },
})
