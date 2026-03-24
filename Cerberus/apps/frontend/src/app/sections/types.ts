import type { TranslationKey } from '../../i18n/messages'
import type { DomainStatusMap } from '../../store/slices/shared'
import type {
  MarketMessage,
  MatchingOrderBook,
  OrderTimelineEvent,
  PersistenceStatus,
  SignalRecord,
  StrategySignal,
} from '../../types/contracts'

export type Translate = (key: TranslationKey) => string

export type HeaderEnv = {
  gateway_base: string
  strategy_base: string
}

export type HeaderProps = {
  t: Translate
  env: HeaderEnv
  locale: 'zh-CN' | 'en-US'
  liveAnnouncement: string
  onLocaleChange: (locale: 'zh-CN' | 'en-US') => void
}

export type MarketSectionProps = {
  t: Translate
  selectedSymbol: string
  displayQuote?: MarketMessage
  latestEvent?: OrderTimelineEvent
  orderSummary: string
  candles: [number, string, string, string, string, string][]
  onSymbolSelect: (symbol: string) => void
}

export type TradingSectionProps = {
  t: Translate
  selectedSymbol: string
  latestBid?: string
  latestAsk?: string
}

export type ExecutionSectionProps = {
  t: Translate
  selectedSymbol: string
  strategySignal?: StrategySignal
  recentSignals: SignalRecord[]
  persistenceStatus?: PersistenceStatus
  summaryError?: string
  matchingOrderBook?: MatchingOrderBook
}

export type HealthSectionProps = {
  domainStatus: DomainStatusMap
  persistenceStatus?: PersistenceStatus
}
