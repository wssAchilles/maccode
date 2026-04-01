import { useMemo } from 'react'

import { useI18n } from '../i18n/I18nProvider'
import type { MatchingOrderBook, MatchingOrderBookLevel } from '../types/contracts'
import { EmptyState, GlassPanel, SectionFrame } from '../ui'

type Props = {
  orderbook?: MatchingOrderBook
}

function LevelGroup({
  title,
  levels,
  tone,
  emptyTitle,
  emptyBody,
}: {
  title: string
  levels: MatchingOrderBookLevel[]
  tone: 'bid' | 'ask'
  emptyTitle: string
  emptyBody: string
}) {
  return (
    <div className="orderbook-group">
      <p className="subtle-label">{title}</p>
      {levels.length === 0 ? (
        <EmptyState title={emptyTitle} body={emptyBody} />
      ) : (
        <div className="stack-sm">
          {levels.map((level, index) => (
            <div key={`${tone}-${index}-${level.price}`} className="orderbook-row">
              <span className={tone === 'bid' ? 'orderbook-price orderbook-price-bid' : 'orderbook-price orderbook-price-ask'}>
                {level.price.toFixed(6)}
              </span>
              <span>{level.total_quantity.toFixed(6)}</span>
              <span>{level.order_count}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function MatchingOrderBookPanel({ orderbook }: Props) {
  const { t } = useI18n()
  const bids = orderbook?.bids ?? []
  const asks = orderbook?.asks ?? []
  const bestBid = bids[0]?.price
  const bestAsk = asks[0]?.price
  const spread = bestBid !== undefined && bestAsk !== undefined ? bestAsk - bestBid : undefined
  const totalBidDepth = bids.reduce((sum, level) => sum + level.total_quantity, 0)
  const totalAskDepth = asks.reduce((sum, level) => sum + level.total_quantity, 0)
  const stale = useMemo(() => {
    if (!orderbook?.generated_at_ms) {
      return true
    }
    return Date.now() - orderbook.generated_at_ms > 8_000
  }, [orderbook?.generated_at_ms])

  const emptyState = useMemo(() => {
    if (!orderbook || orderbook.enabled === false || (orderbook.reason ?? '').includes('matching disabled')) {
      return {
        title: t('orderbook.emptyDisabledTitle'),
        body: t('orderbook.emptyDisabledHint'),
      }
    }
    if (orderbook.degraded && (orderbook.reason ?? '').includes('orderbook_empty')) {
      return {
        title: t('orderbook.empty'),
        body: t('orderbook.emptyNoOrdersHint'),
      }
    }
    if (orderbook.degraded) {
      return {
        title: t('orderbook.emptyDegradedTitle'),
        body: orderbook.reason ?? t('orderbook.emptyDegradedHint'),
      }
    }
    return {
      title: t('orderbook.empty'),
      body: t('orderbook.emptyNoOrdersHint'),
    }
  }, [orderbook, t])

  return (
    <SectionFrame
      title={t('orderbook.title')}
      description={orderbook ? `${orderbook.symbol} · depth ${orderbook.depth}` : t('common.disabled')}
    >
      <div className="orderbook-summary-grid">
        <GlassPanel className="orderbook-summary-card" tone="subtle">
          <p className="subtle-label">{t('market.bestBid')}</p>
          <p className="orderbook-summary-value orderbook-summary-value-bid">
            {bestBid !== undefined ? bestBid.toFixed(6) : '—'}
          </p>
        </GlassPanel>
        <GlassPanel className="orderbook-summary-card" tone="subtle">
          <p className="subtle-label">{t('market.bestAsk')}</p>
          <p className="orderbook-summary-value orderbook-summary-value-ask">
            {bestAsk !== undefined ? bestAsk.toFixed(6) : '—'}
          </p>
        </GlassPanel>
        <GlassPanel className="orderbook-summary-card" tone="subtle">
          <p className="subtle-label">{t('orderbook.spread')}</p>
          <p className="orderbook-summary-value">{spread !== undefined ? spread.toFixed(6) : '—'}</p>
        </GlassPanel>
      </div>

      <div className="orderbook-grid" data-testid="matching-orderbook-panel">
        <LevelGroup
          title={t('orderbook.bids')}
          levels={bids}
          tone="bid"
          emptyTitle={emptyState.title}
          emptyBody={emptyState.body}
        />
        <LevelGroup
          title={t('orderbook.asks')}
          levels={asks}
          tone="ask"
          emptyTitle={emptyState.title}
          emptyBody={emptyState.body}
        />
      </div>
      <GlassPanel className="orderbook-foot" tone="subtle" padded={false}>
        <div className="orderbook-foot-copy">
          <p className="orderbook-updated">
            {t('orderbook.updated')}: {orderbook?.generated_at_ms ? new Date(orderbook.generated_at_ms).toLocaleTimeString() : t('common.na')}
          </p>
          <p className="orderbook-updated">
            {t('orderbook.depthBalance')}: {totalBidDepth.toFixed(3)} / {totalAskDepth.toFixed(3)}
          </p>
        </div>
        {stale ? <p className="orderbook-stale">{t('orderbook.staleHint')}</p> : null}
      </GlassPanel>
    </SectionFrame>
  )
}
