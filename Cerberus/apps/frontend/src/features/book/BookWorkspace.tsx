import { Suspense } from 'react'

import { LazyExecutionTimelinePanel, LazyMatchingOrderBookPanel, PanelSkeleton } from '../../app/lazyPanels'
import { useI18n } from '../../i18n/I18nProvider'
import { DiagnosticDrawer, SectionFrame, WorkspaceOperatorDeck } from '../../ui'
import { SymbolExecutionRail } from '../market/components/SymbolExecutionRail'
import { useBookWorkspaceModel } from './useBookWorkspaceModel'

type Props = {
  active?: boolean
}

export function BookWorkspace({ active = true }: Props) {
  const { t } = useI18n()
  const model = useBookWorkspaceModel({ active })
  const symbolSwitcher = (
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
  )

  return (
    <div className="ws-grid ws-grid-book" data-workspace="book">
      <div className="ws-main stack wsm">
        <Suspense fallback={<PanelSkeleton height="560px" />}>
          <LazyMatchingOrderBookPanel
            model={model.orderbookPanel}
            aside={symbolSwitcher}
            className="ws-primary-panel"
            descriptionMode="srOnly"
          />
        </Suspense>

        <SectionFrame
          title={t('workspace.market.operatorDeckTitle')}
          description={t('workspace.market.operatorDeckDescription')}
          descriptionMode="srOnly"
          accent="teal"
          stage="operator"
          compactHeader
          bodyClassName="operator-shell"
        >
          <WorkspaceOperatorDeck sections={model.operatorSections} layout="rail" />
        </SectionFrame>

        <DiagnosticDrawer title={t('execution.timeline')} summary={t('workspace.market.executionRailDescription')}>
          <Suspense fallback={<PanelSkeleton height="320px" />}>
            <LazyExecutionTimelinePanel active={active} />
          </Suspense>
        </DiagnosticDrawer>
      </div>

      <div className="ws-side stack wss">
        <SectionFrame
          title={t('workspace.market.executionRailTitle')}
          description={t('workspace.market.executionRailDescription')}
          descriptionMode="srOnly"
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
