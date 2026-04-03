import { Suspense } from 'react'

import { LazyExecutionTimelinePanel, LazyMatchingOrderBookPanel, PanelSkeleton } from '../../app/lazyPanels'
import { useI18n } from '../../i18n/I18nProvider'
import { DiagnosticDrawer, MetricTile, SectionFrame, TerminalBand, WorkspaceOperatorDeck, WorkspaceSpotlight } from '../../ui'
import { SymbolExecutionRail } from '../market/components/SymbolExecutionRail'
import { useBookWorkspaceModel } from './useBookWorkspaceModel'

type Props = {
  active?: boolean
}

export function BookWorkspace({ active = true }: Props) {
  const { t } = useI18n()
  const model = useBookWorkspaceModel({ active })

  return (
    <div className="ws-grid ws-grid-book" data-workspace="book">
      <SectionFrame
        title={t('workspace.book.title')}
        description={t('workspace.book.description')}
        eyebrow={t('workspace.book.eyebrow')}
        aside={
          <div className="symbol-switcher">
            {model.symbolChips.map((chip) => (
              <button
                key={chip.id}
                type="button"
                className={chip.active ? 'chip-button chip-button-active' : 'chip-button'}
                onClick={() => model.selectSymbol(chip.id)}
                aria-pressed={chip.active}
              >
                {chip.label}
              </button>
            ))}
          </div>
        }
        className="ws-span-full"
        tone="hero"
        accent="cyan"
        stage="hero"
      >
        <TerminalBand model={model.contextBand} className="hero-band" />
        <div className="ws-hero-grid">
          <WorkspaceSpotlight model={model.spotlight} className="ws-hero-spotlight" />
          <div className="ws-hero-side hero-side-shell">
            <div className="hero-side-head">
              <p className="subtle-label">{t('workspace.hero.readings')}</p>
            </div>
            <div className="metric-grid ws-hero-metrics">
              {model.contextBand.items.slice(0, 4).map((item, index) => (
                <MetricTile
                  key={item.id}
                  label={item.label}
                  value={item.value}
                  tone={item.tone === 'positive' || item.tone === 'negative' || item.tone === 'accent' ? item.tone : 'default'}
                  className={index === 0 ? 'hero-metric hero-metric-primary' : 'hero-metric'}
                />
              ))}
            </div>
          </div>
        </div>
      </SectionFrame>

      <div className="ws-main stack wsm">
        <SectionFrame
          title={t('workspace.market.operatorDeckTitle')}
          description={t('workspace.market.operatorDeckDescription')}
          accent="teal"
          stage="operator"
          compactHeader
          bodyClassName="operator-shell"
        >
          <WorkspaceOperatorDeck sections={model.operatorSections} layout="rail" />
        </SectionFrame>

        <Suspense fallback={<PanelSkeleton height="560px" />}>
          <LazyMatchingOrderBookPanel model={model.orderbookPanel} />
        </Suspense>

        <SectionFrame
          title={t('execution.timeline')}
          description={t('workspace.market.executionRailDescription')}
          accent="amber"
          stage="tail"
          compactHeader
          bodyClassName="tail-shell"
        >
          <Suspense fallback={<PanelSkeleton height="320px" />}>
            <LazyExecutionTimelinePanel active={active} />
          </Suspense>
        </SectionFrame>
      </div>

      <div className="ws-side stack wss">
        <SectionFrame
          title={t('workspace.market.executionRailTitle')}
          description={t('workspace.market.executionRailDescription')}
          accent="amber"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
          <SymbolExecutionRail model={model.executionRail} />
        </SectionFrame>

        {model.summaryError ? (
          <DiagnosticDrawer title={t('workspace.market.diagnostics')} summary={model.summaryError.message}>
            <pre className="diagnostic-pre">{JSON.stringify(model.summaryError, null, 2)}</pre>
          </DiagnosticDrawer>
        ) : null}
      </div>
    </div>
  )
}
