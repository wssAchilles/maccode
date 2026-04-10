import { Suspense } from 'react'

import { LazyHealthInferenceOperationsDrawerContent, PanelSkeleton } from '../../app/lazyPanels'
import { ServiceHealthPanel } from '../../components/ServiceHealthPanel'
import { useI18n } from '../../i18n/I18nProvider'
import type { WorkspaceId } from '../../store/slices/shared'
import { DataList, DiagnosticDrawer, PanelSection, SectionFrame, TerminalBand, WorkspaceOperatorDeck } from '../../ui'
import { useHealthWorkspaceModel } from './useHealthWorkspaceModel'

type Props = {
  active?: boolean
  onSelectWorkspace?: (workspace: WorkspaceId) => void
}

export function HealthWorkspace({ active: _active = true, onSelectWorkspace }: Props) {
  const { t } = useI18n()
  const model = useHealthWorkspaceModel(_active)

  return (
    <div className="ws-grid ws-grid-health" data-workspace="health">
      <div className="ws-main stack wsm">
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
          <ServiceHealthPanel model={model.serviceHealthPanel} />
        </SectionFrame>

        <SectionFrame
          title={t('workspace.health.operatorDeckTitle')}
          description={t('workspace.health.operatorDeckDescription')}
          descriptionMode="srOnly"
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
          descriptionMode="srOnly"
          accent="amber"
          stage="tail"
          compactHeader
        >
          <DiagnosticDrawer
            title={t('workspace.health.persistenceTitle')}
            summary={t('workspace.health.persistenceDescription')}
            contentClassName="tail-drawer"
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
          </DiagnosticDrawer>
        </SectionFrame>
      </div>

      <div className="ws-side stack wss">
        <SectionFrame
          title={t('workspace.inference.title')}
          description={t('workspace.inference.operatorNote')}
          descriptionMode="srOnly"
          accent="cyan"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
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
        </SectionFrame>

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
