import type { TranslationKey } from '../../i18n/messages'
import type { MarketMessage, OrderTimelineEvent, StrategySignal, UIState } from '../../types/contracts'
import { formatConfidence, formatPrice, summarizeLatestFeedback } from '../../view-models/workbench'

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
  items: {
    id: string
    title: string
    subtitle: string
    status: string
    time: string
  }[]
  emptyTitle?: string
  emptyHint?: string
}

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
  const items = orderEvents
    .filter((item) => item.symbol === selectedSymbol)
    .slice(0, 4)
    .map((item) => ({
      id: item.id,
      title: item.event_type,
      subtitle: `${item.symbol ?? selectedSymbol} · ${item.request_id ?? '—'} · ${item.execution_id ?? '—'}`,
      status: item.status ?? '—',
      time: formatDateTime(item.event_time ?? item.received_at),
    }))

  if (items.length === 0) {
    return {
      summary: selectedSymbol,
      items: [],
      emptyTitle: t('workspace.market.executionRailEmpty'),
      emptyHint: t('workspace.market.executionRailDescription'),
    }
  }

  return {
    summary: `${selectedSymbol} · ${items.length}`,
    items,
  }
}
