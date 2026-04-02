import { Suspense } from 'react'

import { LazyHealthInferenceOperationsDrawerContent, PanelSkeleton } from '../../app/lazyPanels'
import { ServiceHealthPanel } from '../../components/ServiceHealthPanel'
import { useI18n } from '../../i18n/I18nProvider'
import { DataList, DiagnosticDrawer, GlassPanel, PanelSection, SectionFrame, TerminalBand, WorkspaceOperatorDeck, WorkspaceSpotlight } from '../../ui'
import { useHealthWorkspaceModel } from './useHealthWorkspaceModel'
import { InferenceDiagnosticsPanel } from '../inference-observability/components/InferenceDiagnosticsPanel'

type Props = {
  active?: boolean
}

export function HealthWorkspace({ active: _active = true }: Props) {
  const { t } = useI18n()
  const model = useHealthWorkspaceModel(_active)

  return (
    <div className="ws-grid ws-grid-health" data-workspace="health">
      <SectionFrame
        title={t('workspace.health.title')}
        description={t('workspace.health.description')}
        eyebrow={t('workspace.health.eyebrow')}
        className="ws-span-full"
        tone="hero"
        accent="teal"
        stage="hero"
      >
        <TerminalBand model={model.contextBand} className="hero-band" />
        <ServiceHealthPanel model={model.serviceHealthPanel} />
      </SectionFrame>

      <div className="ws-main stack wsm">
        <SectionFrame title={t('workspace.health.title')} description={t('workspace.health.description')} accent="teal" stage="feature">
          <WorkspaceSpotlight model={model.spotlight} />
        </SectionFrame>

        <SectionFrame
          title={t('workspace.health.operatorDeckTitle')}
          description={t('workspace.health.operatorDeckDescription')}
          accent="cyan"
          stage="operator"
        >
          <WorkspaceOperatorDeck sections={model.operatorSections} layout="rail" />
        </SectionFrame>

        <SectionFrame title={t('workspace.health.persistenceTitle')} description={t('workspace.health.persistenceDescription')} accent="amber" stage="feature">
          <div className="health-grid hp-tail-grid">
            <PanelSection
              className="hp-tail-section"
              eyebrow={t('workspace.health.operatorPersistenceTitle')}
              title={t('workspace.health.workerSnapshotTitle')}
              hint={t('workspace.health.operatorPersistenceDescription')}
            >
              <DataList items={model.workerItems} />
            </PanelSection>
            <PanelSection
              className="hp-tail-section"
              eyebrow={t('workspace.health.persistenceTitle')}
              title={t('workspace.health.storeSnapshotTitle')}
              hint={t('workspace.health.persistenceDescription')}
            >
              <DataList items={model.storeItems} />
            </PanelSection>
          </div>
        </SectionFrame>

        <SectionFrame title={t('workspace.inference.title')} description={t('workspace.inference.description')} accent="cyan" stage="tail" bodyClassName="tail-shell">
          <InferenceDiagnosticsPanel model={model.inferenceDiagnostics} />
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
        </SectionFrame>
      </div>

      <div className="ws-side stack wss">
        <GlassPanel className="diag-shell" tone="subtle">
          <TerminalBand model={model.diagnosticsBand} className="diag-band" />
        </GlassPanel>
        <DiagnosticDrawer
          title={t('workspace.health.requestIds')}
          summary={t('workspace.health.requestIdsDescription')}
          defaultOpen={model.hasDiagnosticsAlert}
          contentClassName="diag-content"
        >
          <pre className="diagnostic-pre">{JSON.stringify(model.diagnostics, null, 2)}</pre>
        </DiagnosticDrawer>
      </div>
    </div>
  )
}
