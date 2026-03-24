import { useMemo } from 'react'

import { useI18n } from '../i18n/I18nProvider'
import type { MatchingOrderBook, MatchingOrderBookLevel } from '../types/contracts'

type Props = {
  orderbook?: MatchingOrderBook
}

function renderRows(levels: MatchingOrderBookLevel[], side: 'bid' | 'ask', emptyText: string) {
  if (levels.length === 0) {
    return (
      <div className="rounded border border-slate-700/60 bg-slate-900/40 px-2 py-1 text-[11px] text-slate-500">
        {emptyText}
      </div>
    )
  }

  return levels.map((level, index) => (
    <div
      key={`${side}-${index}-${level.price}`}
      className="grid grid-cols-3 gap-2 rounded border border-slate-700/60 bg-slate-900/40 px-2 py-1 text-[11px]"
    >
      <span className={side === 'bid' ? 'text-gain' : 'text-loss'}>{level.price.toFixed(6)}</span>
      <span className="text-slate-300">{level.total_quantity.toFixed(6)}</span>
      <span className="text-slate-400">{level.order_count}</span>
    </div>
  ))
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
    <article className="panel-card" data-testid="matching-orderbook-panel">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="panel-title">{t('orderbook.title')}</h2>
        <span className="text-[11px] text-slate-400">
          {orderbook ? `${orderbook.symbol} depth=${orderbook.depth}` : t('common.disabled')}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <p className="text-[11px] text-slate-400">{t('orderbook.bids')}</p>
          {renderRows(bids, 'bid', t('orderbook.empty'))}
        </div>
        <div className="space-y-1">
          <p className="text-[11px] text-slate-400">{t('orderbook.asks')}</p>
          {renderRows(asks, 'ask', t('orderbook.empty'))}
        </div>
      </div>

      <p className="mt-3 text-[11px] text-slate-500">
        {t('orderbook.updated')}:{' '}
        {orderbook?.generated_at_ms ? new Date(orderbook.generated_at_ms).toLocaleTimeString() : t('common.na')}
      </p>
      {stale ? <p className="text-[11px] text-amber-200">{t('orderbook.stale')}</p> : null}
    </article>
  )
}
