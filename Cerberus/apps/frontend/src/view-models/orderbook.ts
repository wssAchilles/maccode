import type { TranslationKey } from '../i18n/messages'
import type { MatchingOrderBook, MatchingOrderBookLevel } from '../types/contracts'

type Translate = (key: TranslationKey) => string

type PreparedMatchingOrderBook = {
  symbol?: string
  depth?: number
  bids: MatchingOrderBookLevel[]
  asks: MatchingOrderBookLevel[]
  bestBid?: number
  bestAsk?: number
  spread?: number
  totalBidDepth: number
  totalAskDepth: number
  generatedAtMs?: number
  emptyKind: 'disabled' | 'no-orders' | 'degraded' | 'empty'
  degradedReason?: string
}

export type MatchingOrderBookLevelRowModel = {
  id: string
  priceLabel: string
  quantityLabel: string
  orderCountLabel: string
}

export type MatchingOrderBookPanelModel = {
  title: string
  description: string
  bidsTitle: string
  asksTitle: string
  bestBidTitle: string
  bestAskTitle: string
  spreadTitle: string
  updatedTitle: string
  depthBalanceTitle: string
  bids: MatchingOrderBookLevelRowModel[]
  asks: MatchingOrderBookLevelRowModel[]
  bestBidLabel: string
  bestAskLabel: string
  spreadLabel: string
  updatedAtLabel: string
  depthBalanceLabel: string
  emptyTitle: string
  emptyBody: string
  stale: boolean
  staleHint?: string
}

const preparedOrderBookCache = new WeakMap<MatchingOrderBook, PreparedMatchingOrderBook>()

function formatPrice(value?: number): string {
  return value !== undefined ? value.toFixed(6) : '—'
}

function formatQuantity(value: number): string {
  return value.toFixed(6)
}

function prepareMatchingOrderBook(orderbook?: MatchingOrderBook): PreparedMatchingOrderBook {
  if (!orderbook) {
    return {
      bids: [],
      asks: [],
      totalBidDepth: 0,
      totalAskDepth: 0,
      emptyKind: 'disabled',
    }
  }

  const cached = preparedOrderBookCache.get(orderbook)
  if (cached) {
    return cached
  }

  const bids = orderbook.bids ?? []
  const asks = orderbook.asks ?? []
  const bestBid = bids[0]?.price
  const bestAsk = asks[0]?.price

  let emptyKind: PreparedMatchingOrderBook['emptyKind'] = 'empty'
  if (orderbook.enabled === false || (orderbook.reason ?? '').includes('matching disabled')) {
    emptyKind = 'disabled'
  } else if (orderbook.degraded && (orderbook.reason ?? '').includes('orderbook_empty')) {
    emptyKind = 'no-orders'
  } else if (orderbook.degraded) {
    emptyKind = 'degraded'
  }

  const prepared = {
    symbol: orderbook.symbol,
    depth: orderbook.depth,
    bids,
    asks,
    bestBid,
    bestAsk,
    spread: bestBid !== undefined && bestAsk !== undefined ? bestAsk - bestBid : undefined,
    totalBidDepth: bids.reduce((sum, level) => sum + level.total_quantity, 0),
    totalAskDepth: asks.reduce((sum, level) => sum + level.total_quantity, 0),
    generatedAtMs: orderbook.generated_at_ms,
    emptyKind,
    degradedReason: orderbook.reason ?? undefined,
  } satisfies PreparedMatchingOrderBook

  preparedOrderBookCache.set(orderbook, prepared)
  return prepared
}

function buildLevelRows(levels: MatchingOrderBookLevel[], tone: 'bid' | 'ask'): MatchingOrderBookLevelRowModel[] {
  return levels.map((level, index) => ({
    id: `${tone}-${index}-${level.price}`,
    priceLabel: formatPrice(level.price),
    quantityLabel: formatQuantity(level.total_quantity),
    orderCountLabel: String(level.order_count),
  }))
}

function resolveEmptyState(
  prepared: PreparedMatchingOrderBook,
  t: Translate,
): Pick<MatchingOrderBookPanelModel, 'emptyTitle' | 'emptyBody'> {
  if (prepared.emptyKind === 'disabled') {
    return {
      emptyTitle: t('orderbook.emptyDisabledTitle'),
      emptyBody: t('orderbook.emptyDisabledHint'),
    }
  }

  if (prepared.emptyKind === 'no-orders') {
    return {
      emptyTitle: t('orderbook.empty'),
      emptyBody: t('orderbook.emptyNoOrdersHint'),
    }
  }

  if (prepared.emptyKind === 'degraded') {
    return {
      emptyTitle: t('orderbook.emptyDegradedTitle'),
      emptyBody: prepared.degradedReason ?? t('orderbook.emptyDegradedHint'),
    }
  }

  return {
    emptyTitle: t('orderbook.empty'),
    emptyBody: t('orderbook.emptyNoOrdersHint'),
  }
}

export function buildMatchingOrderBookPanelModel({
  t,
  orderbook,
}: {
  t: Translate
  orderbook?: MatchingOrderBook
}): MatchingOrderBookPanelModel {
  const prepared = prepareMatchingOrderBook(orderbook)
  const emptyState = resolveEmptyState(prepared, t)
  const stale = !prepared.generatedAtMs || Date.now() - prepared.generatedAtMs > 8_000

  return {
    title: t('orderbook.title'),
    description:
      prepared.symbol && prepared.depth !== undefined
        ? `${prepared.symbol} · depth ${prepared.depth}`
        : t('common.disabled'),
    bidsTitle: t('orderbook.bids'),
    asksTitle: t('orderbook.asks'),
    bestBidTitle: t('market.bestBid'),
    bestAskTitle: t('market.bestAsk'),
    spreadTitle: t('orderbook.spread'),
    updatedTitle: t('orderbook.updated'),
    depthBalanceTitle: t('orderbook.depthBalance'),
    bids: buildLevelRows(prepared.bids, 'bid'),
    asks: buildLevelRows(prepared.asks, 'ask'),
    bestBidLabel: formatPrice(prepared.bestBid),
    bestAskLabel: formatPrice(prepared.bestAsk),
    spreadLabel: formatPrice(prepared.spread),
    updatedAtLabel: prepared.generatedAtMs ? new Date(prepared.generatedAtMs).toLocaleTimeString() : t('common.na'),
    depthBalanceLabel: `${prepared.totalBidDepth.toFixed(3)} / ${prepared.totalAskDepth.toFixed(3)}`,
    emptyTitle: emptyState.emptyTitle,
    emptyBody: emptyState.emptyBody,
    stale,
    staleHint: stale ? t('orderbook.staleHint') : undefined,
  }
}
