import type { Locale } from '../../i18n/messages'
import type {
  BinanceRule,
  Candle,
  MarketMessage,
  MatchingOrderBook,
  OrderTimelineEvent,
  PersistenceStatus,
  SignalRecord,
  StrategySignal,
  TradingPolicy,
  UIState,
} from '../../types/contracts'

export type DomainName = 'market-stream' | 'strategy-summary' | 'execution-trading'

export type DomainStatusMap = Record<DomainName, UIState>

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
    last_error?: string
  }
  strategySummaryActions: {
    refreshSummary: () => Promise<void>
  }
}

export type ExecutionTradingSlice = {
  executionTrading: {
    latest_event?: OrderTimelineEvent
    order_events: OrderTimelineEvent[]
    heartbeat?: string
    filter_symbol: string
    filter_account_id: string
    trading_policy?: TradingPolicy
    binance_rule?: BinanceRule
  }
  executionTradingActions: {
    connectOrdersSocket: () => void
    loadRecentOrderEvents: () => Promise<void>
    loadTradingPolicy: () => Promise<void>
    loadBinanceRule: (symbol: string) => Promise<void>
    setFilters: (filters: { symbol?: string; account_id?: string }) => void
  }
}

export type UIStateSlice = {
  env: RuntimeEnv
  uiState: {
    locale: Locale
    domain_status: DomainStatusMap
    live_announcement: string
  }
  uiActions: {
    setLocale: (locale: Locale) => void
    setDomainStatus: (
      domain: DomainName,
      patch: Partial<UIState> & { state?: UIState['state'] },
    ) => void
    recomputeStaleFlags: (nowMs?: number) => void
    announce: (message: string) => void
  }
}

export type RootStore = MarketStreamSlice &
  StrategySummarySlice &
  ExecutionTradingSlice &
  UIStateSlice
