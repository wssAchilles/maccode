import type { StateCreator } from 'zustand'

import type { Locale } from '../../i18n/messages'
import { DEFAULT_UI_STATE } from '../../types/contracts'
import { WORKSPACE_IDS } from './shared'
import type {
  CoreFlowMap,
  CoreFlowStep,
  CoreFlowStepId,
  CoreFlowStepState,
  DomainName,
  RootStore,
  UIStateSlice,
  WorkspaceId,
} from './shared'

const LOCALE_KEY = 'cerberus.locale'

const STALE_THRESHOLD_MS = {
  'market-stream': 5_000,
  'strategy-summary': 12_000,
  'execution-trading': 15_000,
} as const

const EMPTY_CORE_FLOW_STEP: CoreFlowStep = {
  state: 'idle',
  last_update_ms: null,
}

const DEFAULT_CORE_FLOW: CoreFlowMap = {
  bootstrap: { ...EMPTY_CORE_FLOW_STEP },
  market: { ...EMPTY_CORE_FLOW_STEP },
  precheck: { ...EMPTY_CORE_FLOW_STEP },
  submit: { ...EMPTY_CORE_FLOW_STEP },
  feedback: { ...EMPTY_CORE_FLOW_STEP },
  cancel: { ...EMPTY_CORE_FLOW_STEP },
}

const DOMAIN_TO_FLOW_STEP: Record<DomainName, CoreFlowStepId> = {
  'market-stream': 'market',
  'strategy-summary': 'bootstrap',
  'execution-trading': 'feedback',
}

function mapDomainStateToCoreState(state: 'idle' | 'loading' | 'ready' | 'degraded' | 'error'): CoreFlowStepState {
  if (state === 'loading') {
    return 'active'
  }
  if (state === 'ready') {
    return 'success'
  }
  if (state === 'degraded') {
    return 'degraded'
  }
  if (state === 'error') {
    return 'error'
  }
  return 'idle'
}

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

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '')
}

function resolveConfiguredBase(raw: string | undefined): string {
  const trimmed = raw?.trim()
  if (!trimmed) {
    return ''
  }
  return trimTrailingSlash(trimmed)
}

function resolveWebSocketBase(httpBase: string): string {
  if (httpBase) {
    return httpBase.replace(/^http/, 'ws')
  }
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}`
  }
  return ''
}

const gatewayBase = resolveConfiguredBase(import.meta.env.VITE_GATEWAY_BASE)
const strategyBase = resolveConfiguredBase(import.meta.env.VITE_STRATEGY_BASE)
const wsBase = resolveWebSocketBase(gatewayBase)
const liveStreamEnabled = import.meta.env.VITE_DISABLE_LIVE_STREAM !== 'true'

function isWorkspaceId(value: string | null): value is WorkspaceId {
  return value !== null && (WORKSPACE_IDS as readonly string[]).includes(value)
}

function resolveWorkspace(): WorkspaceId {
  if (typeof window === 'undefined') {
    return 'overview'
  }

  const params = new URLSearchParams(window.location.search)
  const workspace = params.get('workspace')
  return isWorkspaceId(workspace) ? workspace : 'overview'
}

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
    core_flow: { ...DEFAULT_CORE_FLOW },
    shell_navigation: {
      workspace: resolveWorkspace(),
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
    setWorkspace: (workspace) => {
      set((state) => ({
        uiState: {
          ...state.uiState,
          shell_navigation: {
            workspace,
          },
        },
      }))
    },
    setDomainStatus: (domain, patch) => {
      set((state) => {
        const current = state.uiState.domain_status[domain]
        const hasRequestId = Object.prototype.hasOwnProperty.call(patch, 'request_id')
        const now = patch.last_update_ms ?? Date.now()
        const nextRequestId = hasRequestId ? patch.request_id : current.request_id
        const next = {
          ...current,
          ...patch,
          last_update_ms: now,
          stale: patch.stale ?? false,
          request_id: nextRequestId,
        }
        const flowStep = DOMAIN_TO_FLOW_STEP[domain]
        const currentFlow = state.uiState.core_flow[flowStep]
        const nextFlow = {
          ...currentFlow,
          state: patch.state ? mapDomainStateToCoreState(patch.state) : currentFlow.state,
          last_update_ms: now,
          reason: patch.reason ?? currentFlow.reason,
          request_id: hasRequestId ? patch.request_id : currentFlow.request_id,
        }

        return {
          uiState: {
            ...state.uiState,
            domain_status: {
              ...state.uiState.domain_status,
              [domain]: next,
            },
            core_flow: {
              ...state.uiState.core_flow,
              [flowStep]: nextFlow,
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
        const nextFlow = {
          bootstrap: { ...state.uiState.core_flow.bootstrap },
          market: { ...state.uiState.core_flow.market },
          precheck: { ...state.uiState.core_flow.precheck },
          submit: { ...state.uiState.core_flow.submit },
          feedback: { ...state.uiState.core_flow.feedback },
          cancel: { ...state.uiState.core_flow.cancel },
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
            const mappedStep = DOMAIN_TO_FLOW_STEP[domain]
            nextFlow[mappedStep].state = 'degraded'
            nextFlow[mappedStep].last_update_ms = now
            nextFlow[mappedStep].reason = 'stale data'
          }
        })

        return {
          uiState: {
            ...state.uiState,
            domain_status: next,
            core_flow: nextFlow,
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
    setCoreFlowStep: (step, patch) => {
      set((state) => {
        const current = state.uiState.core_flow[step]
        const next = {
          ...current,
          ...patch,
          last_update_ms: patch.last_update_ms ?? Date.now(),
        }
        return {
          uiState: {
            ...state.uiState,
            core_flow: {
              ...state.uiState.core_flow,
              [step]: next,
            },
          },
        }
      })
    },
  },
})
