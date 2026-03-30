import { ServiceHealthPanel } from '../../components/ServiceHealthPanel'
import { useI18n } from '../../i18n/I18nProvider'
import { DataList, DiagnosticDrawer, GlassPanel, SectionFrame } from '../../ui'
import { useHealthWorkspaceModel } from './useHealthWorkspaceModel'
import { InferenceDiagnosticsPanel } from '../inference-observability/components/InferenceDiagnosticsPanel'
import { InferenceOperationsPanel } from '../inference-observability/components/InferenceOperationsPanel'

type Props = {
  active?: boolean
}

export function HealthWorkspace({ active: _active = true }: Props) {
  const { t } = useI18n()
  const model = useHealthWorkspaceModel()

  return (
    <div className="workspace-grid">
      <SectionFrame
        title={t('workspace.health.title')}
        description={t('workspace.health.description')}
        eyebrow={t('workspace.health.eyebrow')}
        className="workspace-span-full"
      >
        <ServiceHealthPanel domainStatus={model.domainStatus} persistence={model.persistenceStatus} />
      </SectionFrame>

      <div className="workspace-main stack">
        <SectionFrame title={t('workspace.health.persistenceTitle')} description={t('workspace.health.persistenceDescription')}>
          <div className="health-grid">
            <GlassPanel tone="subtle">
              <DataList items={model.workerItems} />
            </GlassPanel>
            <GlassPanel tone="subtle">
              <DataList items={model.storeItems} />
            </GlassPanel>
          </div>
        </SectionFrame>

        <SectionFrame title={t('workspace.inference.title')} description={t('workspace.inference.description')}>
          <InferenceDiagnosticsPanel model={model.inferenceDiagnostics} />
          <InferenceOperationsPanel
            model={model.inferenceOperations.model}
            reason={model.inferenceOperations.reason}
            selectedModelId={model.inferenceOperations.selectedModelId}
            onReasonChange={model.inferenceOperations.setReason}
            onSelectedModelIdChange={model.inferenceOperations.setSelectedModelId}
            onPromote={model.inferenceOperations.onPromote}
            onRollback={model.inferenceOperations.onRollback}
            onActivate={model.inferenceOperations.onActivate}
          />
        </SectionFrame>
      </div>

      <div className="workspace-side stack">
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
