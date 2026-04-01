import type { TranslationKey } from '../../i18n/messages'
import type {
  PersistenceStatus,
  SignalRecord,
} from '../../types/contracts'
import {
  formatConfidence,
  formatDateTimeLabel,
  type PreparedTradingSnapshot,
  type WorkspaceSpotlightModel,
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

export type OverviewRecentSignalCardModel = {
  id: string
  signal: string
  symbol: string
  items: OverviewDataItem[]
}

type BuildOverviewMetricTilesParams = {
  t: Translate
  snapshot: PreparedTradingSnapshot
}

type BuildOverviewPersistenceItemsParams = {
  t: Translate
  persistenceStatus?: PersistenceStatus
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

export function buildOverviewSpotlightModel({
  t,
  snapshot,
  readyCount,
  attentionCount,
}: {
  t: Translate
  snapshot: PreparedTradingSnapshot
  readyCount: number
  attentionCount: number
}): WorkspaceSpotlightModel {
  return {
    summary: `${snapshot.selectedSymbol} · ${snapshot.signalValue} · ${snapshot.feedbackValue ?? t('common.heartbeat')}`,
    hint: `${t('common.updatedAt')}: ${snapshot.feedbackAtValue}`,
    chips: [snapshot.selectedSymbol, snapshot.signalValue],
    metrics: [
      {
        id: 'mid-price',
        label: t('orderbook.midPrice'),
        value: snapshot.midPriceValue,
        tone: 'accent',
      },
      {
        id: 'spread',
        label: t('orderbook.spread'),
        value: snapshot.spreadValue,
      },
      {
        id: 'services-ready',
        label: t('common.ready'),
        value: String(readyCount),
        tone: readyCount > 0 ? 'positive' : 'default',
      },
      {
        id: 'services-attention',
        label: t('workspace.overview.attention'),
        value: String(attentionCount),
        tone: attentionCount > 0 ? 'negative' : 'default',
      },
    ],
  }
}

export function buildOverviewRecentSignalCards({
  t,
  recentSignals,
}: {
  t: Translate
  recentSignals: SignalRecord[]
}): OverviewRecentSignalCardModel[] {
  return recentSignals.slice(0, 4).map((signal) => ({
    id: `${signal.created_at}-${signal.strategy_id}-${signal.symbol}`,
    signal: signal.signal,
    symbol: signal.symbol,
    items: [
      {
        id: 'confidence',
        label: t('strategy.confidence'),
        value: formatConfidence(signal.confidence),
      },
      {
        id: 'strategy',
        label: t('workspace.strategy.auditStrategy'),
        value: signal.strategy_id || '—',
      },
      {
        id: 'createdAt',
        label: t('common.updatedAt'),
        value: formatDateTimeLabel(signal.created_at),
      },
    ],
  }))
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
