import type { UTCTimestamp } from 'lightweight-charts'
import type { TranslationKey } from '../../i18n/messages'
import type { Candle, UIState } from '../../types/contracts'
import { isRealtimeSnapshotStale } from '../../view-models/realtime'
import { type PreparedTradingSnapshot, type WorkspaceSpotlightModel, formatPrice } from '../../view-models/workbench'
import { type PreparedExecutionSelection } from '../execution/read-models'
import type { MatchingOrderBookPanelModel } from '../../view-models/orderbook'

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

export type MarketChartCandleModel = {
  time: UTCTimestamp
  open: number
  high: number
  low: number
  close: number
}

export type MarketChartSeriesModel = {
  points: MarketChartCandleModel[]
  prefixHashes: Uint32Array
  firstTime?: UTCTimestamp
  lastTime?: UTCTimestamp
}

export type MarketChartMarkerModel = {
  id: string
  time: UTCTimestamp
  position: 'belowBar' | 'aboveBar' | 'inBar'
  shape: 'arrowUp' | 'arrowDown' | 'circle'
  color: string
  text: string
}

export const MARKET_SYMBOLS = ['BTCUSDT', 'ETHUSDT'] as const

const preparedCandleCache = new WeakMap<Candle[], MarketChartSeriesModel>()
const preparedMarkerCache = new WeakMap<PreparedExecutionSelection, MarketChartMarkerModel[]>()

type BuildMarketMetricTilesParams = {
  t: Translate
  snapshot: PreparedTradingSnapshot
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

function markerColor(tone: 'positive' | 'negative' | 'accent' | 'muted'): string {
  if (tone === 'positive') {
    return '#15803d'
  }
  if (tone === 'negative') {
    return '#b91c1c'
  }
  if (tone === 'accent') {
    return '#0369a1'
  }
  return '#64748b'
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
  snapshot,
}: BuildMarketMetricTilesParams): MarketMetricTileModel[] {
  return [
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
      id: 'signal',
      label: t('strategy.signal'),
      value: snapshot.signalValue,
      hint: `${t('strategy.confidence')}: ${snapshot.confidenceValue}`,
    },
    {
      id: 'execution-stream',
      label: t('market.orderStream'),
      value: snapshot.feedbackValue ?? t('common.heartbeat'),
    },
  ]
}

export function buildMarketSpotlightModel({
  t,
  snapshot,
  executionRail,
  orderbookPanel,
}: {
  t: Translate
  snapshot: PreparedTradingSnapshot
  executionRail: MarketExecutionRailModel
  orderbookPanel: MatchingOrderBookPanelModel
}): WorkspaceSpotlightModel {
  const latestPulse = executionRail.items[0]

  return {
    summary: t('workspace.market.linkageHint').replace('{symbol}', snapshot.selectedSymbol),
    hint: t('workspace.market.linkageDetail'),
    chips: [
      snapshot.selectedSymbol,
      snapshot.signalValue,
      orderbookPanel.stale ? t('health.stale') : t('health.fresh'),
    ],
    metrics: [
      {
        id: 'mid-price',
        label: t('orderbook.midPrice'),
        value: snapshot.midPriceValue,
        tone: 'accent',
        hint: `${t('common.updatedAt')}: ${snapshot.quoteUpdatedAtValue}`,
      },
      {
        id: 'spread',
        label: t('orderbook.spread'),
        value: snapshot.spreadValue,
      },
      {
        id: 'depth-balance',
        label: t('orderbook.depthBalance'),
        value: orderbookPanel.depthBalanceLabel,
        hint: orderbookPanel.liquidityBiasLabel,
      },
      {
        id: 'execution-pulse',
        label: t('workspace.execution.operationsLatestStatus'),
        value: latestPulse?.status ?? t('common.na'),
        hint: latestPulse?.time ?? executionRail.emptyHint ?? executionRail.staleHint,
        tone: executionRail.state === 'stale' ? 'negative' : 'default',
      },
    ],
  }
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

function hashPart(hash: number, value: string | number): number {
  const text = String(value)
  let nextHash = hash
  for (let index = 0; index < text.length; index += 1) {
    nextHash ^= text.charCodeAt(index)
    nextHash = Math.imul(nextHash, 16777619)
  }
  return nextHash >>> 0
}

export function buildMarketChartSeriesModel(candles: Candle[]): MarketChartSeriesModel {
  const cached = preparedCandleCache.get(candles)
  if (cached) {
    return cached
  }

  const points: MarketChartCandleModel[] = []
  const prefixHashes = new Uint32Array(candles.length)
  let rollingHash = 2166136261

  for (let index = 0; index < candles.length; index += 1) {
    const item = candles[index]
    rollingHash = hashPart(rollingHash, item[0])
    rollingHash = hashPart(rollingHash, item[1])
    rollingHash = hashPart(rollingHash, item[2])
    rollingHash = hashPart(rollingHash, item[3])
    rollingHash = hashPart(rollingHash, item[4])
    prefixHashes[index] = rollingHash

    points.push({
      time: Math.floor(item[0] / 1000) as UTCTimestamp,
      open: Number(item[1]),
      high: Number(item[2]),
      low: Number(item[3]),
      close: Number(item[4]),
    })
  }

  const prepared = {
    points,
    prefixHashes,
    firstTime: points[0]?.time,
    lastTime: points[points.length - 1]?.time,
  }

  preparedCandleCache.set(candles, prepared)
  return prepared
}

function prefixHashAt(series: MarketChartSeriesModel, index: number): number {
  if (index < 0 || index >= series.prefixHashes.length) {
    return 0
  }
  return series.prefixHashes[index] ?? 0
}

export function isSameMarketChartCandle(
  left: MarketChartSeriesModel['points'][number] | undefined,
  right: MarketChartSeriesModel['points'][number] | undefined,
): boolean {
  return (
    left?.time === right?.time &&
    left?.open === right?.open &&
    left?.high === right?.high &&
    left?.low === right?.low &&
    left?.close === right?.close
  )
}

export function getMarketChartReplayStartIndex(
  previous: MarketChartSeriesModel,
  next: MarketChartSeriesModel,
): number {
  if (
    previous.points.length === 0 ||
    next.points.length === 0 ||
    next.points.length < previous.points.length ||
    previous.firstTime !== next.firstTime
  ) {
    return -1
  }

  if (next.points.length === previous.points.length) {
    const previousStablePrefixHash = prefixHashAt(previous, previous.points.length - 2)
    const nextStablePrefixHash = prefixHashAt(next, next.points.length - 2)
    if (previousStablePrefixHash !== nextStablePrefixHash) {
      return -1
    }
    return previous.points.length - 1
  }

  const previousStablePrefixHash = prefixHashAt(previous, previous.points.length - 2)
  const nextStablePrefixHash = prefixHashAt(next, previous.points.length - 2)
  if (previousStablePrefixHash !== nextStablePrefixHash) {
    return -1
  }

  return Math.max(0, previous.points.length - 1)
}

export function buildMarketExecutionRailModel({
  t,
  selectedSymbol,
  preparedSelection,
  nowMs,
}: {
  t: Translate
  selectedSymbol: string
  preparedSelection: PreparedExecutionSelection
  nowMs?: number
}): MarketExecutionRailModel {
  const prepared = preparedSelection
  const { orderModels, latestTimestamp, filledCount } = prepared
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

  const stale = isRealtimeSnapshotStale(latestTimestamp, 120_000, nowMs)

  return {
    summary: `${selectedSymbol} · ${items.length} · ${filledCount} fills`,
    state: stale ? 'stale' : 'ready',
    items,
    staleHint: stale ? t('workspace.market.executionRailStale') : undefined,
  }
}

export function buildMarketChartMarkersModel({
  preparedSelection,
}: {
  preparedSelection: PreparedExecutionSelection
}): MarketChartMarkerModel[] {
  const cached = preparedMarkerCache.get(preparedSelection)
  if (cached) {
    return cached
  }

  const prepared: MarketChartMarkerModel[] = preparedSelection.markers.map((item) => ({
    id: item.id,
    time: Math.floor(item.time / 1000) as UTCTimestamp,
    position:
      item.phase === 'fill'
        ? 'belowBar'
        : item.phase === 'rejected'
          ? 'aboveBar'
          : 'inBar',
    shape:
      item.phase === 'fill'
        ? 'arrowUp'
        : item.phase === 'rejected'
          ? 'arrowDown'
          : 'circle',
    color: markerColor(item.tone),
    text: item.label,
  }))

  preparedMarkerCache.set(preparedSelection, prepared)
  return prepared
}
