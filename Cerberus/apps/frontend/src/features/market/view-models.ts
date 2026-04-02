import type { UTCTimestamp } from 'lightweight-charts'
import type { TranslationKey } from '../../i18n/messages'
import type { Candle, UIState } from '../../types/contracts'
import { isRealtimeSnapshotStale } from '../../view-models/realtime'
import {
  type PreparedTradingSnapshot,
  type WorkspaceContextBandModel,
  type WorkspaceOperatorDeckSectionModel,
  type WorkspaceSpotlightModel,
  formatDateTimeLabel,
  formatEmptyStateLabel,
  formatPrice,
} from '../../view-models/workbench'
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
  band?: WorkspaceContextBandModel
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

export type MarketChartMarkersModel = {
  items: MarketChartMarkerModel[]
  signature: string
}

export type MarketChartContextModel = {
  eyebrow: string
  summary: string
  hint: string
  chips: string[]
  metrics: {
    id: string
    label: string
    value: string
    tone?: 'default' | 'positive' | 'negative' | 'accent'
  }[]
}

export const MARKET_SYMBOLS = ['BTCUSDT', 'ETHUSDT'] as const

const preparedCandleCache = new WeakMap<Candle[], MarketChartSeriesModel>()
const preparedMarkerCache = new WeakMap<PreparedExecutionSelection, MarketChartMarkersModel>()

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
  return phase ?? t('common.na')
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

export function buildMarketHeroBandModel({
  t,
  snapshot,
}: {
  t: Translate
  snapshot: PreparedTradingSnapshot
}): WorkspaceContextBandModel {
  return {
    eyebrow: t('workspace.market.description'),
    title: snapshot.selectedSymbol,
    hint: snapshot.feedbackValue ?? t('common.heartbeat'),
    accent: 'cyan',
    items: [
      {
        id: 'signal',
        label: t('strategy.signal'),
        value: snapshot.signalValue,
        tone: 'accent',
      },
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
        id: 'updated-at',
        label: t('common.updatedAt'),
        value: snapshot.quoteUpdatedAtValue,
      },
    ],
  }
}

export function buildMarketInspectorBandModel({
  t,
  snapshot,
  executionRail,
  orderbookPanel,
}: {
  t: Translate
  snapshot: PreparedTradingSnapshot
  executionRail: MarketExecutionRailModel
  orderbookPanel: MatchingOrderBookPanelModel
}): WorkspaceContextBandModel {
  const latestPulse = executionRail.items[0]

  return {
    eyebrow: t('workspace.market.title'),
    title: snapshot.selectedSymbol,
    hint: orderbookPanel.liquidityBiasLabel,
    accent: orderbookPanel.stale ? 'amber' : 'cyan',
    items: [
      {
        id: 'signal',
        label: t('strategy.signal'),
        value: snapshot.signalValue,
        tone: 'accent',
      },
      {
        id: 'mid',
        label: t('orderbook.midPrice'),
        value: snapshot.midPriceValue,
        tone: 'accent',
      },
      {
        id: 'depth-balance',
        label: t('orderbook.depthBalance'),
        value: orderbookPanel.depthBalanceLabel,
      },
      {
        id: 'total-depth',
        label: t('orderbook.totalDepth'),
        value: orderbookPanel.totalDepthLabel,
      },
      {
        id: 'pulse',
        label: t('workspace.execution.operationsLatestStatus'),
        value: latestPulse?.status ?? executionRail.emptyTitle ?? t('common.na'),
        tone: executionRail.state === 'stale' ? 'negative' : 'default',
      },
      {
        id: 'updated',
        label: t('common.updatedAt'),
        value: latestPulse?.time ?? orderbookPanel.updatedAtLabel,
      },
    ],
  }
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
    accent: orderbookPanel.stale ? 'amber' : 'cyan',
    postureLabel: orderbookPanel.liquidityBiasLabel,
    metrics: [
      {
        id: 'mid-price',
        label: t('orderbook.midPrice'),
        value: snapshot.midPriceValue,
        tone: 'accent',
        hint: `${t('common.updatedAt')}: ${snapshot.quoteUpdatedAtValue}`,
        visualPriority: 'primary',
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

export function buildMarketOperatorSections({
  t,
  snapshot,
  executionRail,
  orderbookPanel,
}: {
  t: Translate
  snapshot: PreparedTradingSnapshot
  executionRail: MarketExecutionRailModel
  orderbookPanel: MatchingOrderBookPanelModel
}): WorkspaceOperatorDeckSectionModel[] {
  const latestPulse = executionRail.items[0]

  return [
    {
      id: 'quote-posture',
      title: t('workspace.market.operatorQuoteTitle'),
      summary: t('workspace.market.operatorQuoteDescription'),
      accent: 'cyan',
      postureLabel: snapshot.selectedSymbol,
      visualPriority: 'hero',
      items: [
        {
          id: 'symbol',
          label: 'Symbol',
          value: snapshot.selectedSymbol,
          tone: 'accent',
        },
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
      ],
    },
    {
      id: 'depth-pulse',
      title: t('workspace.market.operatorDepthTitle'),
      summary: t('workspace.market.operatorDepthDescription'),
      accent: executionRail.state === 'stale' ? 'amber' : 'teal',
      postureLabel: orderbookPanel.liquidityBiasLabel,
      items: [
        {
          id: 'depth-balance',
          label: t('orderbook.depthBalance'),
          value: orderbookPanel.depthBalanceLabel,
        },
        {
          id: 'total-depth',
          label: t('orderbook.totalDepth'),
          value: orderbookPanel.totalDepthLabel,
        },
        {
          id: 'liquidity-bias',
          label: t('orderbook.liquidityBias'),
          value: orderbookPanel.liquidityBiasLabel,
        },
        {
          id: 'pulse-status',
          label: t('workspace.execution.operationsLatestStatus'),
          value: latestPulse?.status ?? executionRail.emptyTitle ?? t('common.na'),
          tone: executionRail.state === 'stale' ? 'negative' : 'default',
        },
        {
          id: 'pulse-time',
          label: t('common.updatedAt'),
          value: latestPulse?.time ?? executionRail.staleHint ?? executionRail.emptyHint ?? t('common.na'),
        },
      ],
    },
  ]
}

export function buildMarketChartContextModel({
  t,
  snapshot,
  executionRail,
  orderbookPanel,
}: {
  t: Translate
  snapshot: PreparedTradingSnapshot
  executionRail: MarketExecutionRailModel
  orderbookPanel: MatchingOrderBookPanelModel
}): MarketChartContextModel {
  const latestPulse = executionRail.items[0]

  return {
    eyebrow: t('workspace.market.chartDescription'),
    summary: `${snapshot.selectedSymbol} · ${snapshot.signalValue}`,
    hint:
      executionRail.state === 'stale'
        ? executionRail.staleHint ?? t('health.stale')
        : latestPulse?.status ?? orderbookPanel.liquidityBiasLabel,
    chips: [
      snapshot.selectedSymbol,
      snapshot.signalValue,
      orderbookPanel.liquidityBiasLabel,
      orderbookPanel.stale ? t('health.stale') : t('health.fresh'),
    ],
    metrics: [
      {
        id: 'mid',
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
        id: 'pulse',
        label: t('workspace.execution.operationsLatestStatus'),
        value: latestPulse?.status ?? t('common.na'),
        tone: executionRail.state === 'stale' ? 'negative' : 'default',
      },
    ],
  }
}

export function buildMarketChartBandModel({
  t,
  snapshot,
  executionRail,
  orderbookPanel,
}: {
  t: Translate
  snapshot: PreparedTradingSnapshot
  executionRail: MarketExecutionRailModel
  orderbookPanel: MatchingOrderBookPanelModel
}): WorkspaceContextBandModel {
  const latestPulse = executionRail.items[0]

  return {
    eyebrow: t('workspace.market.chartDescription'),
    title: snapshot.selectedSymbol,
    hint: orderbookPanel.liquidityBiasLabel,
    items: [
      {
        id: 'signal',
        label: t('strategy.signal'),
        value: snapshot.signalValue,
        tone: 'accent',
      },
      {
        id: 'mid',
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
        id: 'depth',
        label: t('orderbook.depthBalance'),
        value: orderbookPanel.depthBalanceLabel,
      },
      {
        id: 'pulse',
        label: t('workspace.execution.operationsLatestStatus'),
        value: latestPulse?.status ?? t('common.na'),
        tone: executionRail.state === 'stale' ? 'negative' : 'default',
      },
      {
        id: 'freshness',
        label: t('common.updatedAt'),
        value: snapshot.quoteUpdatedAtValue,
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
      title: `${executionPhaseLabel(t, item.latestPhase)} · ${item.side ?? t('common.na')}`,
      subtitle: `${item.symbol ?? selectedSymbol} · ${item.requestId ?? formatEmptyStateLabel('request-id')} · ${item.executionIds[0] ?? item.orderId ?? formatEmptyStateLabel('order-id')}`,
      status: executionPhaseLabel(t, item.latestStatus ?? item.latestPhase),
      time: formatDateTimeLabel(item.fillAt ?? item.canceledAt ?? item.rejectedAt ?? item.acceptedAt ?? item.submitAt),
    }))

  if (items.length === 0) {
    return {
      summary: selectedSymbol,
      band: {
        eyebrow: t('workspace.market.executionRailTitle'),
        title: t('workspace.market.executionRailEmpty'),
        hint: t('workspace.market.executionRailDescription'),
        accent: 'amber',
        items: [
          { id: 'symbol', label: 'Symbol', value: selectedSymbol, tone: 'accent' },
          { id: 'events', label: t('workspace.execution.lifecycleLatest'), value: t('common.na') },
          { id: 'fills', label: t('workspace.execution.lifecycleFilledCount'), value: '0' },
          { id: 'updated', label: t('common.updatedAt'), value: formatEmptyStateLabel('time') },
        ],
      },
      state: 'empty',
      items: [],
      emptyTitle: t('workspace.market.executionRailEmpty'),
      emptyHint: t('workspace.market.executionRailDescription'),
    }
  }

  const stale = isRealtimeSnapshotStale(latestTimestamp, 120_000, nowMs)

  return {
    summary: `${selectedSymbol} · ${items.length} · ${filledCount} fills`,
    band: {
      eyebrow: t('workspace.market.executionRailTitle'),
      title: selectedSymbol,
      hint: stale ? t('workspace.market.executionRailStale') : t('workspace.market.executionRailDescription'),
      accent: stale ? 'amber' : 'cyan',
      items: [
        { id: 'symbol', label: 'Symbol', value: selectedSymbol, tone: 'accent' },
        { id: 'events', label: t('workspace.execution.lifecycleLatest'), value: items[0]?.status ?? t('common.na') },
        { id: 'fills', label: t('workspace.execution.lifecycleFilledCount'), value: String(filledCount) },
        { id: 'updated', label: t('common.updatedAt'), value: items[0]?.time ?? formatEmptyStateLabel('time') },
      ],
    },
    state: stale ? 'stale' : 'ready',
    items,
    staleHint: stale ? t('workspace.market.executionRailStale') : undefined,
  }
}

export function buildMarketChartMarkersModel({
  preparedSelection,
}: {
  preparedSelection: PreparedExecutionSelection
}): MarketChartMarkersModel {
  const cached = preparedMarkerCache.get(preparedSelection)
  if (cached) {
    return cached
  }

  const items: MarketChartMarkerModel[] = preparedSelection.markers.map((item) => ({
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

  const prepared = {
    items,
    signature: items
      .map((item) => `${item.id}:${item.time}:${item.position}:${item.shape}:${item.color}:${item.text}`)
      .join('|'),
  }

  preparedMarkerCache.set(preparedSelection, prepared)
  return prepared
}
