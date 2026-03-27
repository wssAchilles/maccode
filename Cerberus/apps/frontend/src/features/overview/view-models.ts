import type { TranslationKey } from '../../i18n/messages'
import type {
  MarketMessage,
  OrderTimelineEvent,
  PersistenceStatus,
  StrategySignal,
  TradingPolicy,
} from '../../types/contracts'
import {
  formatConfidence,
  formatPrice,
  summarizeLatestEventAt,
  summarizeLatestFeedback,
} from '../../view-models/workbench'

type Translate = (key: TranslationKey) => string

export type OverviewMetricTileModel = {
  id: string
  label: string
  value: string
  tone?: 'default' | 'positive' | 'negative' | 'accent'
  hint?: string
}

export type OverviewDataItem = {
  id: string
  label: string
  value: string
}

type BuildOverviewMetricTilesParams = {
  t: Translate
  selectedSymbol: string
  displayQuote?: MarketMessage
  strategySignal?: StrategySignal
  latestEvent?: OrderTimelineEvent
  heartbeat?: string
}

type BuildOverviewPersistenceItemsParams = {
  t: Translate
  persistenceStatus?: PersistenceStatus
}

type BuildOverviewExecutionSummaryParams = {
  t: Translate
  tradingPolicy?: TradingPolicy
}

export function buildOverviewMetricTiles({
  t,
  selectedSymbol,
  displayQuote,
  strategySignal,
  latestEvent,
  heartbeat,
}: BuildOverviewMetricTilesParams): OverviewMetricTileModel[] {
  return [
    {
      id: 'best-bid',
      label: t('market.bestBid'),
      value: formatPrice(displayQuote?.bid_price),
      tone: 'positive',
      hint: selectedSymbol,
    },
    {
      id: 'best-ask',
      label: t('market.bestAsk'),
      value: formatPrice(displayQuote?.ask_price),
      tone: 'negative',
      hint: selectedSymbol,
    },
    {
      id: 'signal',
      label: t('strategy.signal'),
      value: strategySignal?.signal ?? 'HOLD',
      tone: 'accent',
      hint: `${t('strategy.confidence')}: ${formatConfidence(strategySignal?.confidence)}`,
    },
    {
      id: 'feedback',
      label: t('workspace.overview.feedback'),
      value: summarizeLatestFeedback(latestEvent, heartbeat, t),
      hint: summarizeLatestEventAt(latestEvent),
    },
  ]
}

export function buildOverviewPersistenceItems({
  t,
  persistenceStatus,
}: BuildOverviewPersistenceItemsParams): OverviewDataItem[] {
  return [
    {
      id: 'worker',
      label: t('strategy.ticksProcessed'),
      value: String(persistenceStatus?.worker.processed_ticks ?? 0),
    },
    {
      id: 'supabase',
      label: 'Supabase',
      value: String(persistenceStatus?.stores.supabase_enabled ?? false),
    },
    {
      id: 'firebase',
      label: 'Firestore',
      value: String(persistenceStatus?.stores.firebase_enabled ?? false),
    },
  ]
}

export function buildOverviewExecutionSummary({
  t,
  tradingPolicy,
}: BuildOverviewExecutionSummaryParams): OverviewDataItem[] {
  return [
    {
      id: 'policy',
      label: t('execution.policy'),
      value: tradingPolicy?.enforced ? t('common.ready') : t('common.disabled'),
    },
  ]
}
