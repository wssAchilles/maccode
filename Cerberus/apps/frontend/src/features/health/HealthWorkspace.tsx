import { Suspense } from 'react'

import { LazyHealthInferenceOperationsDrawerContent, PanelSkeleton } from '../../app/lazyPanels'
import { useI18n } from '../../i18n/I18nProvider'
import type { WorkspaceId, WorkspacePanelId } from '../../store/slices/shared'
import { WORKSPACE_PANELS_BY_WORKSPACE } from '../../view-models/workbench'
import {
  DataList,
  DiagnosticDrawer,
  FocusedWorkspacePanel,
  GlassPanel,
  PanelSection,
  SectionFrame,
  StatusPill,
  SubpageLauncher,
  type SubpageLauncherItem,
  TerminalBand,
  WorkspaceOperatorDeck,
} from '../../ui'
import { useHealthWorkspaceModel } from './useHealthWorkspaceModel'

type Props = {
  active?: boolean
  onSelectWorkspace?: (workspace: WorkspaceId) => void
  panel?: WorkspacePanelId
  onSelectPanel?: (panel: WorkspacePanelId) => void
}

export function HealthWorkspace({
  active: _active = true,
  onSelectWorkspace,
  panel = 'home',
  onSelectPanel,
}: Props) {
  const { t } = useI18n()
  const model = useHealthWorkspaceModel(_active)
  const panelItems: SubpageLauncherItem[] = WORKSPACE_PANELS_BY_WORKSPACE.health
    .filter((item) => item.id !== 'home')
    .map((item) => ({
      id: item.id,
      title: t(item.titleKey),
      description: t(item.descriptionKey),
      cta: `${t(item.actionKey)} ${t(item.titleKey)}`,
    }))
  const openHome = () => onSelectPanel?.('home')
  const openPanel = (next: string) => onSelectPanel?.(next as WorkspacePanelId)

  const persistencePanel = (
    <>
      <TerminalBand model={model.persistenceBand} className="tail-band" compact hideHint hideEyebrow />
      <div className="health-grid hp-tail-grid">
        <PanelSection
          className="hp-tail-section"
          eyebrow={t('workspace.health.operatorPersistenceTitle')}
          title={t('workspace.health.workerSnapshotTitle')}
          hint={t('workspace.health.operatorPersistenceDescription')}
          compact
        >
          <DataList items={model.workerItems} />
        </PanelSection>
        <PanelSection
          className="hp-tail-section"
          eyebrow={t('workspace.health.persistenceTitle')}
          title={t('workspace.health.storeSnapshotTitle')}
          hint={t('workspace.health.persistenceDescription')}
          compact
        >
          <DataList items={model.storeItems} />
        </PanelSection>
      </div>
    </>
  )

  const inferenceReadOnlyPanel = (
    <>
      <PanelSection
        className="ifp"
        eyebrow={t('workspace.inference.runtimeStatus')}
        title={model.inferenceDiagnostics.stateLabel}
        hint={model.inferenceDiagnostics.summary}
        compact
      >
        <DataList
          dense
          items={[
            ...model.inferenceDiagnostics.runtimeItems.filter((item) => item.id === 'stateBackend' || item.id === 'stateRestored'),
            ...model.inferenceDiagnostics.rolloutItems.filter((item) => item.id === 'promotion'),
            ...model.inferenceDiagnostics.comparisonItems.filter((item) => item.id === 'comparedTicks'),
            ...model.inferenceDiagnostics.modelItems.filter((item) => item.id === 'macroF1'),
            ...model.inferenceDiagnostics.auditItems.filter((item) => item.id === 'event'),
          ]}
        />
      </PanelSection>
      <div className="ws-actions">
        <button type="button" className="soft-button sbp" onClick={() => onSelectWorkspace?.('inference')}>
          {t('workspace.cta.inference')}
        </button>
        <button type="button" className="soft-button" onClick={() => onSelectWorkspace?.('execution')}>
          {t('workspace.cta.execution')}
        </button>
      </div>
      <DiagnosticDrawer
        title={t('workspace.inference.operationsTitle')}
        summary={model.inferenceDiagnostics.summary}
        testId="health-inference-operations-drawer"
        contentClassName="tail-drawer"
      >
        <Suspense fallback={<PanelSkeleton height="280px" />}>
          <LazyHealthInferenceOperationsDrawerContent active={_active} />
        </Suspense>
      </DiagnosticDrawer>
    </>
  )

  if (panel === 'services') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.health.title')}
        title={t('workspace.health.operatorServiceTitle')}
        description={t('workspace.health.operatorServiceDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <SectionFrame
          title={t('workspace.health.operatorServiceTitle')}
          description={t('workspace.health.operatorServiceDescription')}
          descriptionMode="srOnly"
          className="ws-primary-panel"
          accent="teal"
          stage="feature"
          compactHeader
          bodyClassName="tail-shell"
        >
          <TerminalBand model={model.serviceHealthPanel.band} className="hp-band" compact hideHint hideEyebrow />
          <PanelSection
            className="hp-section"
            eyebrow={t('workspace.health.operatorServiceTitle')}
            title={model.serviceHealthPanel.band.title}
            hideEyebrow
            compact
          >
            <div className="health-grid health-services-grid">
              {model.serviceHealthPanel.cards.map((card) => (
                <GlassPanel key={card.id} className="health-card" tone="subtle">
                  <div className="hc-head">
                    <div>
                      <p className="hc-title">{card.title}</p>
                      <p className="hc-meta">{card.staleLabel}</p>
                    </div>
                    <StatusPill state={card.state} label={card.stateLabel} compact />
                  </div>
                  <p className="hc-updated">
                    {model.serviceHealthPanel.updatedAtLabel}: {card.updatedAt}
                  </p>
                  {card.requestId ? (
                    <p className="hc-request">
                      {model.serviceHealthPanel.requestIdLabel}: {card.requestId}
                    </p>
                  ) : null}
                  {card.reason ? <p className="hc-reason">{card.reason}</p> : null}
                </GlassPanel>
              ))}
            </div>
          </PanelSection>
        </SectionFrame>
        {model.serviceHealthPanel.persistenceGroups.length > 0 ? (
          <SectionFrame
            title={t('workspace.health.persistenceTitle')}
            description={t('workspace.health.persistenceDescription')}
            descriptionMode="srOnly"
            accent="amber"
            stage="tail"
            compactHeader
            bodyClassName="tail-shell"
          >
            <div className="health-grid">
              {model.serviceHealthPanel.persistenceGroups.map((items) => (
                <GlassPanel key={items[0]?.id ?? 'group'} tone="subtle" className="hp-persistence-card">
                  <DataList items={items} />
                </GlassPanel>
              ))}
            </div>
          </SectionFrame>
        ) : null}
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'inference') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.health.title')}
        title={t('workspace.inference.title')}
        description={t('workspace.inference.description')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <SectionFrame
          title={t('workspace.inference.title')}
          description={t('workspace.inference.operatorNote')}
          descriptionMode="srOnly"
          accent="cyan"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
          {inferenceReadOnlyPanel}
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'persistence') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.health.title')}
        title={t('workspace.health.persistenceTitle')}
        description={t('workspace.health.persistenceDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <SectionFrame
          title={t('workspace.health.persistenceTitle')}
          description={t('workspace.health.persistenceDescription')}
          descriptionMode="srOnly"
          accent="amber"
          stage="tail"
          compactHeader
          bodyClassName="tail-shell"
        >
          {persistencePanel}
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'requests') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.health.title')}
        title={t('workspace.health.requestIds')}
        description={t('workspace.health.requestIdsDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <SectionFrame
          title={t('workspace.health.requestIds')}
          description={t('workspace.health.requestIdsDescription')}
          descriptionMode="srOnly"
          accent="cyan"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
          <TerminalBand model={model.diagnosticsBand} className="diag-band" compact hideHint hideEyebrow />
          <pre className="diagnostic-pre">{JSON.stringify(model.diagnostics, null, 2)}</pre>
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  return (
    <div className="ws-grid ws-grid-health" data-workspace="health">
      <div className="workspace-home workspace-home-health">
        <SectionFrame
          title={t('workspace.health.operatorDeckTitle')}
          description={t('workspace.health.operatorDeckDescription')}
          descriptionMode="srOnly"
          className="workspace-home-main ws-primary-panel"
          accent="cyan"
          stage="operator"
          compactHeader
          bodyClassName="operator-shell"
        >
          <WorkspaceOperatorDeck sections={model.operatorSections} layout="rail" />
        </SectionFrame>

        <SubpageLauncher
          title={t('workspace.panel.indexTitle')}
          description={t('workspace.panel.indexHint')}
          items={panelItems}
          onSelect={openPanel}
        />
      </div>
    </div>
  )
}
