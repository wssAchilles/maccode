import { Suspense } from 'react'

import { LazyExecutionTimelinePanel, LazyMatchingOrderBookPanel, PanelSkeleton } from '../../app/lazyPanels'
import { useI18n } from '../../i18n/I18nProvider'
import type { WorkspacePanelId } from '../../store/slices/shared'
import { WORKSPACE_PANELS_BY_WORKSPACE } from '../../view-models/workbench'
import {
  DiagnosticDrawer,
  FocusedWorkspacePanel,
  SectionFrame,
  SubpageLauncher,
  type SubpageLauncherItem,
  TerminalBand,
  WorkspaceOperatorDeck,
  WorkspaceSpotlight,
} from '../../ui'
import { SymbolExecutionRail } from '../market/components/SymbolExecutionRail'
import { useBookWorkspaceModel } from './useBookWorkspaceModel'

type Props = {
  active?: boolean
  panel?: WorkspacePanelId
  onSelectPanel?: (panel: WorkspacePanelId) => void
}

export function BookWorkspace({ active = true, panel = 'home', onSelectPanel }: Props) {
  const { t } = useI18n()
  const model = useBookWorkspaceModel({ active })
  const panelItems: SubpageLauncherItem[] = WORKSPACE_PANELS_BY_WORKSPACE.book
    .filter((item) => item.id !== 'home')
    .map((item) => ({
      id: item.id,
      title: t(item.titleKey),
      description: t(item.descriptionKey),
      cta: `${t(item.actionKey)} ${t(item.titleKey)}`,
    }))
  const openHome = () => onSelectPanel?.('home')
  const openPanel = (next: string) => onSelectPanel?.(next as WorkspacePanelId)
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

  if (panel === 'orderbook') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.book.title')}
        title={t('orderbook.title')}
        description={t('workspace.book.description')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <Suspense fallback={<PanelSkeleton height="560px" />}>
          <LazyMatchingOrderBookPanel
            model={model.orderbookPanel}
            aside={symbolSwitcher}
            className="ws-primary-panel"
            descriptionMode="srOnly"
          />
        </Suspense>
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'depth') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.book.title')}
        title={t('workspace.market.operatorDepthTitle')}
        description={t('workspace.market.operatorDepthDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
        aside={
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
        }
      >
        <SectionFrame
          title={t('workspace.market.operatorDeckTitle')}
          description={t('workspace.market.operatorDeckDescription')}
          descriptionMode="srOnly"
          aside={symbolSwitcher}
          accent="teal"
          stage="operator"
          compactHeader
          bodyClassName="operator-shell"
        >
          <WorkspaceOperatorDeck sections={model.operatorSections} layout="rail" />
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'timeline') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.book.title')}
        title={t('execution.timeline')}
        description={t('workspace.execution.timelineDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <SectionFrame
          title={t('execution.timeline')}
          description={t('workspace.execution.timelineDescription')}
          descriptionMode="srOnly"
          accent="cyan"
          stage="tail"
          compactHeader
        >
          <Suspense fallback={<PanelSkeleton height="320px" />}>
            <LazyExecutionTimelinePanel active={active} />
          </Suspense>
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  return (
    <div className="ws-grid ws-grid-book" data-workspace="book">
      <div className="workspace-home workspace-home-book">
        <SectionFrame
          title={t('workspace.book.title')}
          description={t('workspace.book.description')}
          descriptionMode="srOnly"
          aside={symbolSwitcher}
          className="workspace-home-main ws-primary-panel"
          accent="cyan"
          stage="feature"
        >
          <TerminalBand model={model.contextBand} className="ob-band" compact hideHint hideEyebrow />
          <WorkspaceSpotlight model={model.spotlight} />
        </SectionFrame>

        <SubpageLauncher
          title={t('workspace.panel.indexTitle')}
          description={t('workspace.panel.indexHint')}
          items={panelItems}
          onSelect={openPanel}
        />

        {model.summaryError ? (
          <DiagnosticDrawer title={t('workspace.market.diagnostics')} summary={model.summaryError.message}>
            <pre className="diagnostic-pre">{JSON.stringify(model.summaryError, null, 2)}</pre>
          </DiagnosticDrawer>
        ) : null}
      </div>
    </div>
  )
}
