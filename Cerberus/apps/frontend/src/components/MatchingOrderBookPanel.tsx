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
  emptyText,
}: {
  title: string
  levels: MatchingOrderBookLevel[]
  tone: 'bid' | 'ask'
  emptyText: string
}) {
  return (
    <div className="orderbook-group">
      <p className="subtle-label">{title}</p>
      {levels.length === 0 ? (
        <EmptyState title={emptyText} body="" />
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
  const stale = useMemo(() => {
    if (!orderbook?.generated_at_ms) {
      return true
    }
    return Date.now() - orderbook.generated_at_ms > 8_000
  }, [orderbook?.generated_at_ms])

  return (
    <SectionFrame
      title={t('orderbook.title')}
      description={orderbook ? `${orderbook.symbol} · depth ${orderbook.depth}` : t('common.disabled')}
    >
      <div className="orderbook-grid" data-testid="matching-orderbook-panel">
        <LevelGroup title={t('orderbook.bids')} levels={bids} tone="bid" emptyText={t('orderbook.empty')} />
        <LevelGroup title={t('orderbook.asks')} levels={asks} tone="ask" emptyText={t('orderbook.empty')} />
      </div>
      <GlassPanel className="orderbook-foot" tone="subtle" padded={false}>
        <p className="orderbook-updated">
          {t('orderbook.updated')}: {orderbook?.generated_at_ms ? new Date(orderbook.generated_at_ms).toLocaleTimeString() : t('common.na')}
        </p>
        {stale ? <p className="orderbook-stale">{t('orderbook.stale')}</p> : null}
      </GlassPanel>
    </SectionFrame>
  )
}
