import { Suspense } from 'react'

import { LazyCandlesChart, PanelSkeleton } from '../lazyPanels'
import { buildMarketChartSeriesModel } from '../../features/market/view-models'
import type { MarketSectionProps } from './types'

export function MarketSection({
  t,
  className,
  selectedSymbol,
  displayQuote,
  latestEvent,
  orderSummary,
  candles,
  onSymbolSelect,
}: MarketSectionProps) {
  const sectionClassName = className ?? 'mt-6'

  return (
    <section className={sectionClassName} aria-label={t('section.market')}>
      <h2 className="section-title">{t('section.market')}</h2>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        <article className="metric-card">
          <p className="metric-label">{t('market.bestBid')}</p>
          <p className="metric-value text-gain">{displayQuote?.bid_price ?? '--'}</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">{t('market.bestAsk')}</p>
          <p className="metric-value text-loss">{displayQuote?.ask_price ?? '--'}</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">{t('market.orderStream')}</p>
          <p className="mt-1 text-xs text-cyan-200">{latestEvent?.channel ?? t('common.heartbeat')}</p>
          <p className="mt-1 truncate text-xs text-slate-200">{orderSummary}</p>
        </article>
      </div>

      <article className="panel-card mt-4">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h3 className="panel-title">
            {selectedSymbol} {t('market.candles')}
          </h3>
          <div className="flex gap-2 text-xs">
            {['BTCUSDT', 'ETHUSDT'].map((symbol) => (
              <button
                key={symbol}
                type="button"
                onClick={() => onSymbolSelect(symbol)}
                className={`symbol-chip ${selectedSymbol === symbol ? 'symbol-chip-active' : ''}`}
              >
                {symbol}
              </button>
            ))}
          </div>
        </div>
        <div className="min-h-[340px]">
          <Suspense fallback={<PanelSkeleton height="h-[340px]" />}>
            <LazyCandlesChart series={buildMarketChartSeriesModel(candles)} />
          </Suspense>
        </div>
      </article>
    </section>
  )
}
