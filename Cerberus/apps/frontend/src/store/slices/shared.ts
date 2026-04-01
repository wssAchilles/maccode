import type { Locale } from '../../i18n/messages'
import type {
  AppError,
  BinanceRule,
  Candle,
  InferenceCatalogResponse,
  InferenceControlResult,
  InferenceStatusPayload,
  MarketMessage,
  MatchingOrderBook,
  OrderTimelineEvent,
  PersistenceStatus,
  SignalRecord,
  StrategySignal,
  StrategyOrchestrationControlResult,
  StrategyOrchestrationStatus,
  TradingPolicy,
  UIState,
} from '../../types/contracts'

export type DomainName = 'market-stream' | 'strategy-summary' | 'execution-trading'

export type DomainStatusMap = Record<DomainName, UIState>

export type WorkspaceId = 'overview' | 'market' | 'execution' | 'health'

export type ShellNavigationState = {
  workspace: WorkspaceId
}

export type CoreFlowStepId = 'bootstrap' | 'market' | 'precheck' | 'submit' | 'feedback' | 'cancel'

export type CoreFlowStepState = 'idle' | 'active' | 'success' | 'degraded' | 'error'

export type CoreFlowStep = {
  state: CoreFlowStepState
  last_update_ms: number | null
  reason?: string
  request_id?: string
}

export type CoreFlowMap = Record<CoreFlowStepId, CoreFlowStep>

export type RuntimeEnv = {
  gateway_base: string
  strategy_base: string
  ws_base: string
  live_stream_enabled: boolean
}

export type MarketStreamSlice = {
  marketStream: {
    selected_symbol: string
    latest?: MarketMessage
    latest_by_symbol: Record<string, MarketMessage>
    candles: Candle[]
  }
  marketStreamActions: {
    setSelectedSymbol: (symbol: string) => void
    connectMarketSocket: () => void
    loadCandles: () => Promise<void>
  }
}

export type StrategySummarySlice = {
  strategySummary: {
    signal?: StrategySignal
    recent_signals: SignalRecord[]
    persistence_status?: PersistenceStatus
    matching_orderbook?: MatchingOrderBook
    inference_status?: InferenceStatusPayload
    inference_catalog?: InferenceCatalogResponse
    inference_last_result?: InferenceControlResult
    inference_pending_action?: string
    orchestration_status?: StrategyOrchestrationStatus
    orchestration_last_result?: StrategyOrchestrationControlResult
    orchestration_pending_action?: string
    last_error?: AppError
  }
  strategySummaryActions: {
    refreshSummary: () => Promise<void>
    loadInferenceCatalog: () => Promise<void>
    requestInferencePromotion: (reason?: string) => Promise<void>
    requestInferenceRollback: (reason?: string) => Promise<void>
    activateInferenceModel: (modelId: string, version?: string, reason?: string) => Promise<void>
    loadStrategyOrchestration: () => Promise<void>
    updateStrategyOrchestrationEntry: (
      strategyId: string,
      patch: {
        enabled?: boolean
        priority?: number
        observe_weight?: number
        primary_weight?: number
        symbol_coverage?: string[]
        conflict_targets?: string[]
        downgrade_action?: string
      },
      reason?: string,
    ) => Promise<void>
    updateStrategyOrchestrationPolicies: (
      patch: {
        conflict_policy?: string
        downgrade_policy?: string
      },
      reason?: string,
    ) => Promise<void>
  }
}

export type ExecutionTradingSlice = {
  executionTrading: {
    latest_event?: OrderTimelineEvent
    order_events: OrderTimelineEvent[]
    heartbeat?: string
    filter_symbol: string
    filter_account_id: string
    filter_status: string
    trading_policy?: TradingPolicy
    binance_rule?: BinanceRule
  }
  executionTradingActions: {
    connectOrdersSocket: () => void
    loadRecentOrderEvents: (filters?: {
      symbol?: string
      account_id?: string
      order_id?: string
      status?: string
      request_id?: string
    }) => Promise<void>
    loadTradingPolicy: () => Promise<void>
    loadBinanceRule: (symbol: string) => Promise<void>
    setFilters: (filters: { symbol?: string; account_id?: string; status?: string }) => void
  }
}

export type UIStateSlice = {
  env: RuntimeEnv
  uiState: {
    locale: Locale
    domain_status: DomainStatusMap
    live_announcement: string
    core_flow: CoreFlowMap
    shell_navigation: ShellNavigationState
  }
  uiActions: {
    setLocale: (locale: Locale) => void
    setWorkspace: (workspace: WorkspaceId) => void
    setDomainStatus: (
      domain: DomainName,
      patch: Partial<UIState> & { state?: UIState['state'] },
    ) => void
    recomputeStaleFlags: (nowMs?: number) => void
    announce: (message: string) => void
    setCoreFlowStep: (
      step: CoreFlowStepId,
      patch: Partial<CoreFlowStep> & { state?: CoreFlowStepState },
    ) => void
  }
}

export type RootStore = MarketStreamSlice &
  StrategySummarySlice &
  ExecutionTradingSlice &
  UIStateSlice
