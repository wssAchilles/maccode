import type { TranslationKey } from '../../i18n/messages'
import type {
  PersistenceStatus,
  TradingPolicy,
} from '../../types/contracts'
import {
  type PreparedTradingSnapshot,
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
  snapshot: PreparedTradingSnapshot
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
  snapshot,
}: BuildOverviewMetricTilesParams): OverviewMetricTileModel[] {
  return [
    {
      id: 'best-bid',
      label: t('market.bestBid'),
      value: snapshot.bestBidValue,
      tone: 'positive',
      hint: snapshot.selectedSymbol,
    },
    {
      id: 'best-ask',
      label: t('market.bestAsk'),
      value: snapshot.bestAskValue,
      tone: 'negative',
      hint: snapshot.selectedSymbol,
    },
    {
      id: 'signal',
      label: t('strategy.signal'),
      value: snapshot.signalValue,
      tone: 'accent',
      hint: `${t('strategy.confidence')}: ${snapshot.confidenceValue}`,
    },
    {
      id: 'feedback',
      label: t('workspace.overview.feedback'),
      value: snapshot.feedbackValue ?? t('common.heartbeat'),
      hint: snapshot.feedbackAtValue,
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
