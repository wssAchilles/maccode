import { useI18n } from '../../i18n/I18nProvider'
import type { WorkspaceId } from '../../store/slices/shared'
import { DataList, DiagnosticDrawer, PanelSection, SectionFrame, TerminalBand, WorkspaceOperatorDeck, WorkspaceSpotlight } from '../../ui'
import { InferenceAuditTimeline } from '../inference-observability/components/InferenceAuditTimeline'
import { InferenceOperationsPanel } from '../inference-observability/components/InferenceOperationsPanel'
import { InferenceStatusCard } from '../inference-observability/components/InferenceStatusCard'
import { InferenceSymbolComparisonPanel } from '../inference-observability/components/InferenceSymbolComparisonPanel'
import { useInferenceWorkspaceModel } from './useInferenceWorkspaceModel'

type Props = {
  active?: boolean
  onSelectWorkspace?: (workspace: WorkspaceId) => void
}

export function InferenceWorkspace({ active = true, onSelectWorkspace }: Props) {
  const { t } = useI18n()
  const model = useInferenceWorkspaceModel({ active })

  return (
    <div className="ws-grid ws-grid-inference" data-workspace="inference">
      <SectionFrame
        title={t('workspace.inference.title')}
        description={t('workspace.inference.description')}
        eyebrow={t('workspace.inference.title')}
        className="ws-span-full"
        tone="hero"
        accent="teal"
        stage="hero"
      >
        <TerminalBand model={model.diagnostics.band} className="hero-band" />
        <WorkspaceSpotlight model={model.spotlight} className="ws-hero-spotlight" />
      </SectionFrame>

      <div className="ws-main stack wsm">
        <SectionFrame
          title={t('workspace.inference.operatorDeckTitle')}
          description={t('workspace.inference.operatorDeckDescription')}
          accent="teal"
          stage="operator"
          compactHeader
          bodyClassName="operator-shell"
        >
          <WorkspaceOperatorDeck sections={model.operatorSections} layout="rail" />
        </SectionFrame>

        <SectionFrame
          title={t('workspace.inference.runtimeStatus')}
          description={t('workspace.inference.description')}
          accent="cyan"
          stage="feature"
        >
          <InferenceStatusCard model={model.inferenceCard} onOpenHealth={() => onSelectWorkspace?.('health')} />
        </SectionFrame>

        <SectionFrame
          title={t('workspace.inference.comparisonSummary')}
          description={t('workspace.inference.symbolComparison')}
          accent="cyan"
          stage="feature"
        >
          <InferenceSymbolComparisonPanel model={model.diagnostics} />
        </SectionFrame>
      </div>

      <div className="ws-side stack wss">
        <SectionFrame
          title={t('workspace.inference.model')}
          description={t('workspace.inference.description')}
          accent="cyan"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
          <TerminalBand model={model.diagnostics.band} className="inspector-band" compact hideHint hideEyebrow />
          <PanelSection
            className="tail-card"
            eyebrow={t('workspace.inference.rolloutSummary')}
            title={model.diagnostics.stateLabel}
            hint={model.diagnostics.reason ?? model.diagnostics.summary}
            compact
          >
            <DataList dense items={model.diagnostics.rolloutItems} />
          </PanelSection>
          <PanelSection
            className="tail-card"
            eyebrow={t('workspace.inference.model')}
            title={model.diagnostics.summary}
            hint={t('workspace.inference.description')}
            compact
          >
            <DataList dense items={model.diagnostics.modelItems} />
          </PanelSection>
        </SectionFrame>

        <SectionFrame
          title={t('workspace.inference.auditTimeline')}
          description={t('workspace.inference.recentAudit')}
          accent="amber"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
          <InferenceAuditTimeline model={model.diagnostics} />
        </SectionFrame>

        <SectionFrame
          title={t('workspace.inference.operationsTitle')}
          description={t('workspace.inference.operatorNote')}
          accent="teal"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
          <InferenceOperationsPanel
            model={model.operations.model}
            reason={model.operations.reason}
            selectedModelId={model.operations.selectedModelId}
            onReasonChange={model.operations.setReason}
            onSelectedModelIdChange={model.operations.setSelectedModelId}
            onPromote={() => void model.operations.onPromote()}
            onRollback={() => void model.operations.onRollback()}
            onActivate={() => void model.operations.onActivate()}
          />
        </SectionFrame>

        {model.summaryError ? (
          <DiagnosticDrawer title={t('workspace.inference.operationStatus')} summary={model.summaryError.message}>
            <pre className="diagnostic-pre">{JSON.stringify(model.summaryError, null, 2)}</pre>
          </DiagnosticDrawer>
        ) : null}
      </div>
    </div>
  )
}
