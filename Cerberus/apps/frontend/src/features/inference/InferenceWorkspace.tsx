import { useI18n } from '../../i18n/I18nProvider'
import type { WorkspaceId, WorkspacePanelId } from '../../store/slices/shared'
import { WORKSPACE_PANELS_BY_WORKSPACE } from '../../view-models/workbench'
import {
  DataList,
  DiagnosticDrawer,
  FocusedWorkspacePanel,
  PanelSection,
  SectionFrame,
  SubpageLauncher,
  type SubpageLauncherItem,
  TerminalBand,
} from '../../ui'
import { InferenceAuditTimeline } from '../inference-observability/components/InferenceAuditTimeline'
import { InferenceOperationsPanel } from '../inference-observability/components/InferenceOperationsPanel'
import { InferenceStatusCard } from '../inference-observability/components/InferenceStatusCard'
import { InferenceSymbolComparisonPanel } from '../inference-observability/components/InferenceSymbolComparisonPanel'
import { useInferenceWorkspaceModel } from './useInferenceWorkspaceModel'

type Props = {
  active?: boolean
  onSelectWorkspace?: (workspace: WorkspaceId) => void
  panel?: WorkspacePanelId
  onSelectPanel?: (panel: WorkspacePanelId) => void
}

export function InferenceWorkspace({
  active = true,
  onSelectWorkspace,
  panel = 'home',
  onSelectPanel,
}: Props) {
  const { t } = useI18n()
  const model = useInferenceWorkspaceModel({ active })
  const panelItems: SubpageLauncherItem[] = WORKSPACE_PANELS_BY_WORKSPACE.inference
    .filter((item) => item.id !== 'home')
    .map((item) => ({
      id: item.id,
      title: t(item.titleKey),
      description: t(item.descriptionKey),
      cta: `${t(item.actionKey)} ${t(item.titleKey)}`,
    }))
  const openHome = () => onSelectPanel?.('home')
  const openPanel = (next: string) => onSelectPanel?.(next as WorkspacePanelId)

  const runtimeSection = (
    <SectionFrame
      title={t('workspace.inference.runtimeStatus')}
      description={t('workspace.inference.description')}
      descriptionMode="srOnly"
      className="ws-primary-panel"
      accent="cyan"
      stage="feature"
    >
      <InferenceStatusCard model={model.inferenceCard} onOpenHealth={() => onSelectWorkspace?.('health')} />
    </SectionFrame>
  )

  const modelSection = (
    <SectionFrame
      title={t('workspace.inference.model')}
      description={t('workspace.inference.description')}
      descriptionMode="srOnly"
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
  )

  if (panel === 'runtime') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.inference.title')}
        title={t('workspace.inference.runtimeStatus')}
        description={t('workspace.inference.description')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
        className="fwp-inference-runtime"
      >
        {runtimeSection}
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'comparison') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.inference.title')}
        title={t('workspace.inference.comparisonSummary')}
        description={t('workspace.inference.symbolComparison')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <SectionFrame
          title={t('workspace.inference.comparisonSummary')}
          description={t('workspace.inference.symbolComparison')}
          descriptionMode="srOnly"
          accent="cyan"
          stage="feature"
        >
          <InferenceSymbolComparisonPanel model={model.diagnostics} />
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'model') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.inference.title')}
        title={t('workspace.inference.model')}
        description={t('workspace.inference.registryTitle')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        {modelSection}
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'audit') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.inference.title')}
        title={t('workspace.inference.auditTimeline')}
        description={t('workspace.inference.recentAudit')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <SectionFrame
          title={t('workspace.inference.auditTimeline')}
          description={t('workspace.inference.recentAudit')}
          descriptionMode="srOnly"
          accent="amber"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
          <InferenceAuditTimeline model={model.diagnostics} />
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'controls') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.inference.title')}
        title={t('workspace.inference.operationsTitle')}
        description={t('workspace.inference.operatorNote')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <SectionFrame
          title={t('workspace.inference.operationsTitle')}
          description={t('workspace.inference.operatorNote')}
          descriptionMode="srOnly"
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
      </FocusedWorkspacePanel>
    )
  }

  return (
    <div className="ws-grid ws-grid-inference" data-workspace="inference">
      <div className="workspace-home workspace-home-inference">
        {runtimeSection}
        <SubpageLauncher
          title={t('workspace.panel.indexTitle')}
          description={t('workspace.panel.indexHint')}
          items={panelItems}
          onSelect={openPanel}
        />
        {model.summaryError ? (
          <DiagnosticDrawer title={t('workspace.inference.operationStatus')} summary={model.summaryError.message}>
            <pre className="diagnostic-pre">{JSON.stringify(model.summaryError, null, 2)}</pre>
          </DiagnosticDrawer>
        ) : null}
      </div>
    </div>
  )
}
