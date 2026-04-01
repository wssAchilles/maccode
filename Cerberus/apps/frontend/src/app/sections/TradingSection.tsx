import { Suspense } from 'react'

import { LazyExecutionConsole, PanelSkeleton } from '../lazyPanels'
import type { TradingSectionProps } from './types'

export function TradingSection({ t, className, selectedSymbol, latestBid, latestAsk }: TradingSectionProps) {
  const sectionClassName = className ?? 'mt-6'

  return (
    <section className={sectionClassName} aria-label={t('workspace.execution.ticketTitle')}>
      <h2 className="section-title">{t('workspace.execution.ticketTitle')}</h2>
      <div className="min-h-[540px]">
        <Suspense fallback={<PanelSkeleton height="h-[540px]" />}>
          <LazyExecutionConsole selectedSymbol={selectedSymbol} latestBid={latestBid} latestAsk={latestAsk} />
        </Suspense>
      </div>
    </section>
  )
}
