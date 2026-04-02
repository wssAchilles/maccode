import type { TranslationKey } from '../../i18n/messages'
import type {
  PersistenceStatus,
  SignalRecord,
} from '../../types/contracts'
import {
  formatConfidence,
  formatDateTimeLabel,
  type PreparedTradingSnapshot,
  type WorkspaceContextBandModel,
  type WorkspaceOperatorDeckSectionModel,
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

export function buildOverviewContextBandModel({
  t,
  snapshot,
  readyCount,
  attentionCount,
}: {
  t: Translate
  snapshot: PreparedTradingSnapshot
  readyCount: number
  attentionCount: number
}): WorkspaceContextBandModel {
  return {
    eyebrow: t('workspace.overview.title'),
    title: snapshot.selectedSymbol,
    hint: t('workspace.overview.operatorDeckDescription'),
    accent: attentionCount > 0 ? 'amber' : 'cyan',
    items: [
      {
        id: 'signal',
        label: t('strategy.signal'),
        value: snapshot.signalValue,
        tone: 'accent',
      },
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
        id: 'feedback',
        label: t('workspace.overview.feedback'),
        value: snapshot.feedbackValue ?? t('common.heartbeat'),
      },
      {
        id: 'ready',
        label: t('common.ready'),
        value: String(readyCount),
        tone: readyCount > 0 ? 'positive' : 'default',
      },
      {
        id: 'attention',
        label: t('workspace.overview.attention'),
        value: String(attentionCount),
        tone: attentionCount > 0 ? 'negative' : 'default',
      },
    ],
  }
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
    accent: attentionCount > 0 ? 'amber' : 'cyan',
    postureLabel: attentionCount > 0 ? t('workspace.overview.attention') : t('common.ready'),
    metrics: [
      {
        id: 'mid-price',
        label: t('orderbook.midPrice'),
        value: snapshot.midPriceValue,
        tone: 'accent',
        visualPriority: 'primary',
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

export function buildOverviewOperatorSections({
  t,
  snapshot,
  readyCount,
  attentionCount,
  recentSignalCount,
}: {
  t: Translate
  snapshot: PreparedTradingSnapshot
  readyCount: number
  attentionCount: number
  recentSignalCount: number
}): WorkspaceOperatorDeckSectionModel[] {
  return [
    {
      id: 'signal-posture',
      title: t('workspace.overview.operatorSignalTitle'),
      summary: t('workspace.overview.operatorSignalDescription'),
      accent: 'cyan',
      postureLabel: snapshot.signalValue,
      visualPriority: 'hero',
      items: [
        {
          id: 'symbol',
          label: 'Symbol',
          value: snapshot.selectedSymbol,
          tone: 'accent',
        },
        {
          id: 'signal',
          label: t('strategy.signal'),
          value: snapshot.signalValue,
          tone: 'accent',
        },
        {
          id: 'confidence',
          label: t('strategy.confidence'),
          value: snapshot.confidenceValue,
        },
        {
          id: 'feedback',
          label: t('workspace.overview.feedback'),
          value: snapshot.feedbackValue ?? t('common.heartbeat'),
        },
        {
          id: 'feedback-at',
          label: t('common.updatedAt'),
          value: snapshot.feedbackAtValue,
        },
      ],
    },
    {
      id: 'service-posture',
      title: t('workspace.overview.operatorServiceTitle'),
      summary: t('workspace.overview.operatorServiceDescription'),
      accent: attentionCount > 0 ? 'amber' : 'teal',
      postureLabel: attentionCount > 0 ? t('workspace.overview.attention') : t('common.ready'),
      items: [
        {
          id: 'best-bid',
          label: t('market.bestBid'),
          value: snapshot.bestBidValue,
          tone: 'positive',
        },
        {
          id: 'best-ask',
          label: t('market.bestAsk'),
          value: snapshot.bestAskValue,
          tone: 'negative',
        },
        {
          id: 'ready-count',
          label: t('common.ready'),
          value: String(readyCount),
          tone: readyCount > 0 ? 'positive' : 'default',
        },
        {
          id: 'attention-count',
          label: t('workspace.overview.attention'),
          value: String(attentionCount),
          tone: attentionCount > 0 ? 'negative' : 'default',
        },
        {
          id: 'recent-signals',
          label: t('strategy.recent'),
          value: String(recentSignalCount),
        },
      ],
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
