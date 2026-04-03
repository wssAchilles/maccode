import { Suspense } from 'react'

import { LazyHealthInferenceOperationsDrawerContent, PanelSkeleton } from '../../app/lazyPanels'
import { ServiceHealthPanel } from '../../components/ServiceHealthPanel'
import { useI18n } from '../../i18n/I18nProvider'
import { DataList, DiagnosticDrawer, PanelSection, SectionFrame, TerminalBand, WorkspaceOperatorDeck, WorkspaceSpotlight } from '../../ui'
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
        <div className="ws-hero-grid">
          <WorkspaceSpotlight model={model.spotlight} className="ws-hero-spotlight" />
          <div className="ws-hero-side hero-side-shell">
            <div className="hero-side-head">
              <p className="subtle-label">{t('workspace.hero.readings')}</p>
            </div>
            <ServiceHealthPanel model={model.serviceHealthPanel} />
          </div>
        </div>
      </SectionFrame>

      <div className="ws-main stack wsm">
        <SectionFrame
          title={t('workspace.health.operatorDeckTitle')}
          description={t('workspace.health.operatorDeckDescription')}
          accent="cyan"
          stage="operator"
          compactHeader
          bodyClassName="operator-shell"
        >
          <WorkspaceOperatorDeck sections={model.operatorSections} layout="rail" />
        </SectionFrame>

        <SectionFrame
          title={t('workspace.health.persistenceTitle')}
          description={t('workspace.health.persistenceDescription')}
          accent="amber"
          stage="feature"
          compactHeader
          bodyClassName="tail-shell"
        >
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
        </SectionFrame>

        <SectionFrame title={t('workspace.inference.title')} description={t('workspace.inference.description')} accent="cyan" stage="tail" compactHeader bodyClassName="tail-shell">
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
        <SectionFrame
          title={t('workspace.health.requestIds')}
          description={t('workspace.health.requestIdsDescription')}
          accent="cyan"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
          <TerminalBand model={model.diagnosticsBand} className="diag-band" compact hideHint hideEyebrow />
          <DiagnosticDrawer
            title={t('workspace.health.requestIds')}
            summary={t('workspace.health.requestIdsDescription')}
            defaultOpen={model.hasDiagnosticsAlert}
            contentClassName="diag-content"
          >
            <pre className="diagnostic-pre">{JSON.stringify(model.diagnostics, null, 2)}</pre>
          </DiagnosticDrawer>
        </SectionFrame>
      </div>
    </div>
  )
}
