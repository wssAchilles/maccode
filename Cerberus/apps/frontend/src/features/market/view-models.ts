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
