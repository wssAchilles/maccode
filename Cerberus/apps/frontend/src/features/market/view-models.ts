import type { TranslationKey } from '../../i18n/messages'
import type { MarketMessage, OrderTimelineEvent, StrategySignal, UIState } from '../../types/contracts'
import { formatConfidence, formatPrice, summarizeLatestFeedback } from '../../view-models/workbench'
import { buildExecutionMarkers, buildExecutionOrderReadModels, type ExecutionMarker } from '../execution/read-models'

type Translate = (key: TranslationKey) => string

export type MarketMetricTileModel = {
  id: string
  label: string
  value: string
  tone?: 'default' | 'positive' | 'negative' | 'accent'
  hint?: string
}

export type MarketSymbolChipModel = {
  id: string
  label: string
  active: boolean
}

export type MarketChartState = 'ready' | 'loading' | 'empty' | 'error'

export type MarketChartStateModel = {
  state: MarketChartState
  title: string
  hint: string
}

export type MarketExecutionRailModel = {
  summary: string
  state: 'ready' | 'empty' | 'stale'
  items: {
    id: string
    title: string
    subtitle: string
    status: string
    time: string
  }[]
  staleHint?: string
  emptyTitle?: string
  emptyHint?: string
}

export type MarketChartMarkerModel = ExecutionMarker

export const MARKET_SYMBOLS = ['BTCUSDT', 'ETHUSDT'] as const

type BuildMarketMetricTilesParams = {
  t: Translate
  displayQuote?: MarketMessage
  strategySignal?: StrategySignal
  latestEvent?: OrderTimelineEvent
}

type BuildMarketChartStateParams = {
  t: Translate
  candlesCount: number
  candlesFetching: boolean
  marketStatus: UIState
}

function formatDateTime(value?: string | number): string {
  if (!value) {
    return '—'
  }
  const parsed = typeof value === 'number' ? value : Date.parse(value)
  if (Number.isNaN(parsed)) {
    return typeof value === 'string' ? value : '—'
  }
  return new Date(parsed).toLocaleString()
}

function executionPhaseLabel(t: Translate, phase?: string): string {
  if (phase === 'accepted' || phase === 'submit') {
    return t('workspace.execution.lifecycleStatus.submitted')
  }
  if (phase === 'partial_fill') {
    return t('workspace.execution.lifecycleStatus.partialFill')
  }
  if (phase === 'fill') {
    return t('workspace.execution.lifecycleStatus.filled')
  }
  if (phase === 'rejected') {
    return t('workspace.execution.lifecycleStatus.rejected')
  }
  if (phase === 'cancel_requested') {
    return t('workspace.execution.lifecycleStatus.cancelRequested')
  }
  if (phase === 'canceled') {
    return t('workspace.execution.lifecycleStatus.canceled')
  }
  return phase ?? '—'
}

export function buildMarketSymbolChips(selectedSymbol: string): MarketSymbolChipModel[] {
  return MARKET_SYMBOLS.map((symbol) => ({
    id: symbol,
    label: symbol,
    active: selectedSymbol === symbol,
  }))
}

export function buildMarketMetricTiles({
  t,
  displayQuote,
  strategySignal,
  latestEvent,
}: BuildMarketMetricTilesParams): MarketMetricTileModel[] {
  return [
    {
      id: 'best-bid',
      label: t('market.bestBid'),
      value: formatPrice(displayQuote?.bid_price),
      tone: 'positive',
    },
    {
      id: 'best-ask',
      label: t('market.bestAsk'),
      value: formatPrice(displayQuote?.ask_price),
      tone: 'negative',
    },
    {
      id: 'signal',
      label: t('strategy.signal'),
      value: strategySignal?.signal ?? 'HOLD',
      hint: `${t('strategy.confidence')}: ${formatConfidence(strategySignal?.confidence)}`,
    },
    {
      id: 'execution-stream',
      label: t('market.orderStream'),
      value: summarizeLatestFeedback(latestEvent, undefined, t),
    },
  ]
}

export function buildMarketChartStateModel({
  t,
  candlesCount,
  candlesFetching,
  marketStatus,
}: BuildMarketChartStateParams): MarketChartStateModel {
  if (candlesCount > 0) {
    return {
      state: 'ready',
      title: '',
      hint: '',
    }
  }

  if (candlesFetching || marketStatus.state === 'loading') {
    return {
      state: 'loading',
      title: t('market.chartLoadingTitle'),
      hint: t('market.chartLoadingHint'),
    }
  }

  if (marketStatus.state === 'error') {
    return {
      state: 'error',
      title: t('market.chartErrorTitle'),
      hint: marketStatus.reason ?? t('market.chartRetryHint'),
    }
  }

  return {
    state: 'empty',
    title: t('market.chartEmptyTitle'),
    hint: t('market.chartRetryHint'),
  }
}

export function buildMarketExecutionRailModel({
  t,
  orderEvents,
  selectedSymbol,
}: {
  t: Translate
  orderEvents: OrderTimelineEvent[]
  selectedSymbol: string
}): MarketExecutionRailModel {
  const orderModels = buildExecutionOrderReadModels(orderEvents, selectedSymbol)
  const items = orderModels.slice(0, 4).map((item) => ({
      id: item.id,
      title: `${executionPhaseLabel(t, item.latestPhase)} · ${item.side ?? '—'}`,
      subtitle: `${item.symbol ?? selectedSymbol} · ${item.requestId ?? '—'} · ${item.executionIds[0] ?? item.orderId ?? '—'}`,
      status: executionPhaseLabel(t, item.latestStatus ?? item.latestPhase),
      time: formatDateTime(item.fillAt ?? item.canceledAt ?? item.rejectedAt ?? item.acceptedAt ?? item.submitAt),
    }))

  if (items.length === 0) {
    return {
      summary: selectedSymbol,
      state: 'empty',
      items: [],
      emptyTitle: t('workspace.market.executionRailEmpty'),
      emptyHint: t('workspace.market.executionRailDescription'),
    }
  }

  const latestTimestamp = orderModels[0]
    ? orderModels[0].fillAt ??
      orderModels[0].canceledAt ??
      orderModels[0].rejectedAt ??
      orderModels[0].acceptedAt ??
      orderModels[0].submitAt
    : undefined
  const stale = typeof latestTimestamp === 'number' ? Date.now() - latestTimestamp > 120_000 : false

  return {
    summary: `${selectedSymbol} · ${items.length} · ${orderModels.filter((item) => item.latestPhase === 'fill').length} fills`,
    state: stale ? 'stale' : 'ready',
    items,
    staleHint: stale ? t('workspace.market.executionRailStale') : undefined,
  }
}

export function buildMarketChartMarkersModel({
  orderEvents,
  selectedSymbol,
}: {
  orderEvents: OrderTimelineEvent[]
  selectedSymbol: string
}): MarketChartMarkerModel[] {
  return buildExecutionMarkers(orderEvents, selectedSymbol)
}
