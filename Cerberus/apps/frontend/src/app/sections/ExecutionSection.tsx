import { Suspense } from 'react'

import { AppErrorNotice } from '../../components/common/AppErrorNotice'
import {
  LazyCoreFlowPanel,
  LazyExecutionTimelinePanel,
  LazyMatchingOrderBookPanel,
  PanelSkeleton,
} from '../lazyPanels'
import type { ExecutionSectionProps } from './types'

export function ExecutionSection({
  t,
  className,
  selectedSymbol,
  strategySignal,
  recentSignals,
  persistenceStatus,
  summaryError,
  matchingOrderBook,
}: ExecutionSectionProps) {
  const sectionClassName = className ?? 'mt-6'

  return (
    <section className={sectionClassName} aria-label={t('section.execution')}>
      <h2 className="section-title">{t('section.execution')}</h2>
      <div className="mt-3 grid gap-4 lg:grid-cols-3">
        <div className="min-h-[180px] lg:col-span-3">
          <Suspense fallback={<PanelSkeleton height="h-[180px]" />}>
            <LazyCoreFlowPanel />
          </Suspense>
        </div>

        <article className="panel-card">
          <h3 className="panel-title">{t('strategy.signal')}</h3>
          <p className="mt-2 text-lg font-semibold text-cyan-300">
            {strategySignal?.signal ?? 'HOLD'}
            <span className="ml-2 text-xs text-slate-400">{strategySignal?.symbol ?? selectedSymbol}</span>
          </p>
          <p className="mt-1 text-xs text-slate-300">
            {t('strategy.confidence')}: {strategySignal?.confidence?.toFixed(6) ?? '0.000000'}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            {t('strategy.ticksProcessed')}: {persistenceStatus?.worker.processed_ticks ?? 0}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            {t('strategy.persistence')}: supabase[{String(persistenceStatus?.stores.supabase_enabled)}] firestore[
            {String(persistenceStatus?.stores.firebase_enabled)}]
          </p>
          {summaryError ? <AppErrorNotice error={summaryError} className="mt-2" /> : null}

          <h4 className="mt-4 text-xs text-slate-400">{t('strategy.recent')}</h4>
          <div className="mt-1 max-h-56 space-y-2 overflow-auto">
            {recentSignals.length === 0 ? (
              <p className="text-xs text-slate-500">{t('strategy.noData')}</p>
            ) : (
              recentSignals.map((item, index) => (
                <div key={`${item.created_at}-${index}`} className="rounded-lg border border-slate-700/70 p-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-cyan-200">{item.signal}</span>
                    <span className="text-slate-400">{item.symbol}</span>
                  </div>
                  <p className="mt-1 text-[11px] text-slate-500">{new Date(item.created_at).toLocaleString()}</p>
                </div>
              ))
            )}
          </div>
        </article>

        <div className="min-h-[300px]">
          <Suspense fallback={<PanelSkeleton height="h-[300px]" />}>
            <LazyMatchingOrderBookPanel orderbook={matchingOrderBook} />
          </Suspense>
        </div>
        <div className="min-h-[320px] lg:col-span-2">
          <Suspense fallback={<PanelSkeleton height="h-[320px]" />}>
            <LazyExecutionTimelinePanel />
          </Suspense>
        </div>
      </div>
    </section>
  )
}
