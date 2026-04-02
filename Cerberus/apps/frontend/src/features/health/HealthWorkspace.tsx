import { Suspense } from 'react'

import { LazyHealthInferenceOperationsDrawerContent, PanelSkeleton } from '../../app/lazyPanels'
import { ServiceHealthPanel } from '../../components/ServiceHealthPanel'
import { useI18n } from '../../i18n/I18nProvider'
import { DataList, DiagnosticDrawer, GlassPanel, SectionFrame, WorkspaceOperatorDeck, WorkspaceSpotlight } from '../../ui'
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
          <div className="health-grid">
            <GlassPanel tone="subtle">
              <DataList items={model.workerItems} />
            </GlassPanel>
            <GlassPanel tone="subtle">
              <DataList items={model.storeItems} />
            </GlassPanel>
          </div>
        </SectionFrame>

        <SectionFrame title={t('workspace.inference.title')} description={t('workspace.inference.description')} accent="cyan" stage="tail">
          <InferenceDiagnosticsPanel model={model.inferenceDiagnostics} />
          <DiagnosticDrawer
            title={t('workspace.inference.operationsTitle')}
            summary={model.inferenceDiagnostics.summary}
            testId="health-inference-operations-drawer"
          >
            <Suspense fallback={<PanelSkeleton height="280px" />}>
              <LazyHealthInferenceOperationsDrawerContent active={_active} />
            </Suspense>
          </DiagnosticDrawer>
        </SectionFrame>
      </div>

      <div className="ws-side stack wss">
        <DiagnosticDrawer
          title={t('workspace.health.requestIds')}
          summary={t('workspace.health.requestIdsDescription')}
          defaultOpen={model.hasDiagnosticsAlert}
        >
          <pre className="diagnostic-pre">{JSON.stringify(model.diagnostics, null, 2)}</pre>
        </DiagnosticDrawer>
      </div>
    </div>
  )
}
