import type { TranslationKey } from '../i18n/messages'
import type { MatchingOrderBook, MatchingOrderBookLevel } from '../types/contracts'
import type { WorkspaceContextBandModel } from './workbench'
import { formatEmptyStateLabel } from './workbench'
import { formatOptionalTimeLabel, isRealtimeSnapshotStale } from './realtime'

type Translate = (key: TranslationKey) => string

type PreparedMatchingOrderBook = {
  symbol?: string
  depth?: number
  bids: MatchingOrderBookLevelRowModel[]
  asks: MatchingOrderBookLevelRowModel[]
  bestBidLabel: string
  bestAskLabel: string
  midPriceLabel: string
  spreadLabel: string
  depthBalanceLabel: string
  totalDepthLabel: string
  liquidityBiasLabel: string
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
  band: WorkspaceContextBandModel
  bidsTitle: string
  asksTitle: string
  priceColumnTitle: string
  quantityColumnTitle: string
  orderCountColumnTitle: string
  bestBidTitle: string
  bestAskTitle: string
  midPriceTitle: string
  spreadTitle: string
  updatedTitle: string
  depthBalanceTitle: string
  totalDepthTitle: string
  liquidityBiasTitle: string
  bids: MatchingOrderBookLevelRowModel[]
  asks: MatchingOrderBookLevelRowModel[]
  bestBidLabel: string
  bestAskLabel: string
  midPriceLabel: string
  spreadLabel: string
  updatedAtLabel: string
  depthBalanceLabel: string
  totalDepthLabel: string
  liquidityBiasLabel: string
  emptyTitle: string
  emptyBody: string
  stale: boolean
  staleHint?: string
}

const preparedOrderBookCache = new WeakMap<MatchingOrderBook, PreparedMatchingOrderBook>()

function formatPrice(value?: number, fallback = formatEmptyStateLabel('generic')): string {
  return value !== undefined ? value.toFixed(6) : fallback
}

function formatQuantity(value: number): string {
  return value.toFixed(6)
}

function prepareMatchingOrderBook(orderbook?: MatchingOrderBook): PreparedMatchingOrderBook {
  if (!orderbook) {
    return {
      bids: [],
      asks: [],
      bestBidLabel: formatEmptyStateLabel('bid'),
      bestAskLabel: formatEmptyStateLabel('ask'),
      midPriceLabel: formatEmptyStateLabel('mid'),
      spreadLabel: formatEmptyStateLabel('spread'),
      depthBalanceLabel: '0.000 / 0.000',
      totalDepthLabel: '0.000',
      liquidityBiasLabel: formatEmptyStateLabel('mid'),
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
  const totalBidDepth = bids.reduce((sum, level) => sum + level.total_quantity, 0)
  const totalAskDepth = asks.reduce((sum, level) => sum + level.total_quantity, 0)
  const totalDepth = totalBidDepth + totalAskDepth
  const depthBalanceRatio = totalDepth > 0 ? totalBidDepth / totalDepth : undefined
  const midPrice = bestBid !== undefined && bestAsk !== undefined ? (bestBid + bestAsk) / 2 : undefined

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
    bids: buildLevelRows(bids, 'bid'),
    asks: buildLevelRows(asks, 'ask'),
    bestBidLabel: formatPrice(bestBid, formatEmptyStateLabel('bid')),
    bestAskLabel: formatPrice(bestAsk, formatEmptyStateLabel('ask')),
    midPriceLabel: formatPrice(midPrice, formatEmptyStateLabel('mid')),
    spreadLabel: formatPrice(
      bestBid !== undefined && bestAsk !== undefined ? bestAsk - bestBid : undefined,
      formatEmptyStateLabel('spread'),
    ),
    depthBalanceLabel: `${totalBidDepth.toFixed(3)} / ${totalAskDepth.toFixed(3)}`,
    totalDepthLabel: totalDepth.toFixed(3),
    liquidityBiasLabel:
      depthBalanceRatio === undefined
        ? formatEmptyStateLabel('mid')
        : depthBalanceRatio >= 0.58
          ? 'bid-heavy'
          : depthBalanceRatio <= 0.42
            ? 'ask-heavy'
            : 'balanced',
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
  nowMs,
}: {
  t: Translate
  orderbook?: MatchingOrderBook
  nowMs?: number
}): MatchingOrderBookPanelModel {
  const prepared = prepareMatchingOrderBook(orderbook)
  const emptyState = resolveEmptyState(prepared, t)
  const stale = isRealtimeSnapshotStale(prepared.generatedAtMs, 8_000, nowMs)

  return {
    title: t('orderbook.title'),
    description:
      prepared.symbol && prepared.depth !== undefined
        ? `${prepared.symbol} · depth ${prepared.depth}`
        : t('common.disabled'),
    band: {
      eyebrow: t('orderbook.title'),
      title: prepared.symbol ?? t('orderbook.empty'),
      hint: stale ? t('orderbook.staleHint') : prepared.symbol && prepared.depth !== undefined ? `${prepared.symbol} · depth ${prepared.depth}` : t('common.disabled'),
      accent: stale ? 'amber' : 'cyan',
      items: [
        {
          id: 'best-bid',
          label: t('market.bestBid'),
          value: prepared.bestBidLabel,
          tone: 'positive',
        },
        {
          id: 'best-ask',
          label: t('market.bestAsk'),
          value: prepared.bestAskLabel,
          tone: 'negative',
        },
        {
          id: 'mid-price',
          label: t('orderbook.midPrice'),
          value: prepared.midPriceLabel,
          tone: 'accent',
        },
        {
          id: 'spread',
          label: t('orderbook.spread'),
          value: prepared.spreadLabel,
        },
        {
          id: 'updated',
          label: t('orderbook.updated'),
          value: formatOptionalTimeLabel(prepared.generatedAtMs, t('common.na')),
        },
      ],
    },
    bidsTitle: t('orderbook.bids'),
    asksTitle: t('orderbook.asks'),
    priceColumnTitle: t('orderbook.priceColumn'),
    quantityColumnTitle: t('orderbook.quantityColumn'),
    orderCountColumnTitle: t('orderbook.orderCountColumn'),
    bestBidTitle: t('market.bestBid'),
    bestAskTitle: t('market.bestAsk'),
    midPriceTitle: t('orderbook.midPrice'),
    spreadTitle: t('orderbook.spread'),
    updatedTitle: t('orderbook.updated'),
    depthBalanceTitle: t('orderbook.depthBalance'),
    totalDepthTitle: t('orderbook.totalDepth'),
    liquidityBiasTitle: t('orderbook.liquidityBias'),
    bids: prepared.bids,
    asks: prepared.asks,
    bestBidLabel: prepared.bestBidLabel,
    bestAskLabel: prepared.bestAskLabel,
    midPriceLabel: prepared.midPriceLabel,
    spreadLabel: prepared.spreadLabel,
    updatedAtLabel: formatOptionalTimeLabel(prepared.generatedAtMs, t('common.na')),
    depthBalanceLabel: prepared.depthBalanceLabel,
    totalDepthLabel: prepared.totalDepthLabel,
    liquidityBiasLabel:
      prepared.liquidityBiasLabel === 'bid-heavy'
        ? t('orderbook.liquidityBias.bidHeavy')
        : prepared.liquidityBiasLabel === 'ask-heavy'
          ? t('orderbook.liquidityBias.askHeavy')
          : prepared.liquidityBiasLabel === 'balanced'
            ? t('orderbook.liquidityBias.balanced')
            : t('orderbook.liquidityBiasPending'),
    emptyTitle: emptyState.emptyTitle,
    emptyBody: emptyState.emptyBody,
    stale,
    staleHint: stale ? t('orderbook.staleHint') : undefined,
  }
}
