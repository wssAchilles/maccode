import { Suspense } from 'react'

import { LazyExecutionConsole, PanelSkeleton } from '../lazyPanels'
import type { TradingSectionProps } from './types'

export function TradingSection({ t, selectedSymbol, latestBid, latestAsk }: TradingSectionProps) {
  return (
    <section className="mt-6" aria-label={t('section.trading')}>
      <h2 className="section-title">{t('section.trading')}</h2>
      <div className="min-h-[540px]">
        <Suspense fallback={<PanelSkeleton height="h-[540px]" />}>
          <LazyExecutionConsole selectedSymbol={selectedSymbol} latestBid={latestBid} latestAsk={latestAsk} />
        </Suspense>
      </div>
    </section>
  )
}
