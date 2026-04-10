import { Suspense } from 'react'

import {
  LazyExecutionConsole,
  LazyExecutionTimelinePanel,
  PanelSkeleton,
} from '../../app/lazyPanels'
import { useI18n } from '../../i18n/I18nProvider'
import type { WorkspaceId, WorkspacePanelId } from '../../store/slices/shared'
import { WORKSPACE_PANELS_BY_WORKSPACE } from '../../view-models/workbench'
import {
  DiagnosticDrawer,
  FocusedWorkspacePanel,
  SectionFrame,
  SubpageLauncher,
  type SubpageLauncherItem,
  TerminalBand,
} from '../../ui'
import { ExecutionOperationsPanel } from './components/ExecutionOperationsPanel'
import { ExecutionLifecyclePanel } from '../strategy-orchestration/components/ExecutionLifecyclePanel'
import { useExecutionWorkspaceModel } from './useExecutionWorkspaceModel'

type Props = {
  active?: boolean
  onSelectWorkspace?: (workspace: WorkspaceId) => void
  panel?: WorkspacePanelId
  onSelectPanel?: (panel: WorkspacePanelId) => void
}

export function ExecutionWorkspace({
  active = true,
  onSelectWorkspace,
  panel = 'home',
  onSelectPanel,
}: Props) {
  const { t } = useI18n()
  const model = useExecutionWorkspaceModel({ active })
  const panelItems: SubpageLauncherItem[] = WORKSPACE_PANELS_BY_WORKSPACE.execution
    .filter((item) => item.id !== 'home')
    .map((item) => ({
      id: item.id,
      title: t(item.titleKey),
      description: t(item.descriptionKey),
      cta: `${t(item.actionKey)} ${t(item.titleKey)}`,
    }))
  const openHome = () => onSelectPanel?.('home')
  const openPanel = (next: string) => onSelectPanel?.(next as WorkspacePanelId)

  const linkageActions = (
    <>
      <button type="button" className="soft-button sbp" onClick={() => onSelectWorkspace?.('book')}>
        {t('workspace.cta.book')}
      </button>
      <button type="button" className="soft-button" onClick={() => onSelectWorkspace?.('market')}>
        {t('workspace.cta.market')}
      </button>
      <button type="button" className="soft-button" onClick={() => onSelectWorkspace?.('strategy')}>
        {t('workspace.cta.strategy')}
      </button>
    </>
  )

  if (panel === 'order') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.execution.title')}
        title={t('workspace.execution.ticketTitle')}
        description={t('workspace.execution.ticketDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
        actions={linkageActions}
        className="fwp-execution-order"
      >
        <Suspense fallback={<PanelSkeleton height="540px" />}>
          <LazyExecutionConsole
            active={active}
            selectedSymbol={model.selectedSymbol}
            latestBid={model.displayQuote?.bid_price}
            latestAsk={model.displayQuote?.ask_price}
            density="focused"
          />
        </Suspense>
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'ops') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.execution.title')}
        title={t('workspace.execution.operationsTitle')}
        description={t('workspace.execution.operationsDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <SectionFrame
          title={t('workspace.execution.operationsTitle')}
          description={t('workspace.execution.operationsDescription')}
          descriptionMode="srOnly"
          accent="amber"
          stage="tail"
          compactHeader
        >
          <ExecutionOperationsPanel model={model.operationsPanel} />
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'timeline') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.execution.title')}
        title={t('execution.timeline')}
        description={t('workspace.execution.timelineDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <SectionFrame
          title={t('execution.timeline')}
          description={t('workspace.execution.timelineDescription')}
          descriptionMode="srOnly"
          className="xts"
          accent="cyan"
          stage="tail"
          compactHeader
          bodyClassName="tail-shell"
        >
          <Suspense fallback={<PanelSkeleton height="320px" />}>
            <LazyExecutionTimelinePanel active={active} />
          </Suspense>
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'lifecycle') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.execution.title')}
        title={t('workspace.execution.lifecycleTitle')}
        description={t('workspace.execution.lifecycleDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <SectionFrame
          title={t('workspace.execution.lifecycleTitle')}
          description={t('workspace.execution.lifecycleDescription')}
          descriptionMode="srOnly"
          accent="cyan"
          stage="tail"
          compactHeader
        >
          <ExecutionLifecyclePanel model={model.lifecyclePanel} />
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  return (
    <div className="ws-grid ws-grid-execution" data-workspace="execution">
      <div className="workspace-home workspace-home-execution">
        <SectionFrame
          title={t('workspace.execution.operatorDeckTitle')}
          description={t('workspace.execution.operatorDeckDescription')}
          descriptionMode="srOnly"
          className="workspace-home-main ws-primary-panel"
          accent="teal"
          stage="operator"
          compactHeader
          bodyClassName="operator-shell"
        >
          <TerminalBand model={model.inspectorBand} className="xo-band" compact hideHint hideEyebrow />
          <div className="ws-actions">
            <button type="button" className="soft-button sbp" onClick={() => onSelectWorkspace?.('book')}>
              {t('workspace.cta.book')}
            </button>
            <button type="button" className="soft-button" onClick={() => onSelectWorkspace?.('market')}>
              {t('workspace.cta.market')}
            </button>
            <button type="button" className="soft-button" onClick={() => onSelectWorkspace?.('strategy')}>
              {t('workspace.cta.strategy')}
            </button>
          </div>
        </SectionFrame>

        <SubpageLauncher
          title={t('workspace.panel.indexTitle')}
          description={t('workspace.panel.indexHint')}
          items={panelItems}
          onSelect={openPanel}
        />

        {model.summaryError ? (
          <DiagnosticDrawer title={t('workspace.execution.diagnostics')} summary={model.summaryError.message}>
            <pre className="diagnostic-pre">{JSON.stringify(model.summaryError, null, 2)}</pre>
          </DiagnosticDrawer>
        ) : null}
      </div>
    </div>
  )
}
