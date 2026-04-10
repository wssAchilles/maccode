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
import { StrategyDecisionMatrix } from '../strategy-orchestration/components/StrategyDecisionMatrix'
import { StrategyOrchestrationAuditTimeline } from '../strategy-orchestration/components/StrategyOrchestrationAuditTimeline'
import { StrategyOrchestrationOperationsPanel } from '../strategy-orchestration/components/StrategyOrchestrationOperationsPanel'
import { StrategyRegistryPanel } from '../strategy-orchestration/components/StrategyRegistryPanel'
import { useStrategyWorkspaceModel } from './useStrategyWorkspaceModel'

type Props = {
  active?: boolean
  onSelectWorkspace?: (workspace: WorkspaceId) => void
  panel?: WorkspacePanelId
  onSelectPanel?: (panel: WorkspacePanelId) => void
}

export function StrategyWorkspace({
  active = true,
  onSelectWorkspace,
  panel = 'home',
  onSelectPanel,
}: Props) {
  const { t } = useI18n()
  const model = useStrategyWorkspaceModel({ active })
  const panelItems: SubpageLauncherItem[] = WORKSPACE_PANELS_BY_WORKSPACE.strategy
    .filter((item) => item.id !== 'home')
    .map((item) => ({
      id: item.id,
      title: t(item.titleKey),
      description: t(item.descriptionKey),
      cta: `${t(item.actionKey)} ${t(item.titleKey)}`,
    }))
  const openHome = () => onSelectPanel?.('home')
  const openPanel = (next: string) => onSelectPanel?.(next as WorkspacePanelId)

  const decisionPanel = (
    <SectionFrame
      title={t('workspace.strategy.matrixTitle')}
      description={t('workspace.strategy.description')}
      descriptionMode="srOnly"
      className="ws-primary-panel"
      accent="cyan"
      stage="feature"
      compactHeader
    >
      <StrategyDecisionMatrix model={model.strategyMatrix} />
    </SectionFrame>
  )

  const decisionActions = (
    <>
      <button type="button" className="soft-button" onClick={() => onSelectWorkspace?.('execution')}>
        {t('workspace.cta.execution')}
      </button>
      <button type="button" className="soft-button" onClick={() => onSelectWorkspace?.('inference')}>
        {t('workspace.cta.inference')}
      </button>
    </>
  )

  const homeSummaryPanel = (
    <SectionFrame
      title={t('workspace.strategy.matrixTitle')}
      description={t('workspace.strategy.description')}
      descriptionMode="srOnly"
      className="workspace-home-main ws-primary-panel"
      accent="cyan"
      stage="feature"
      compactHeader
      bodyClassName="operator-shell"
    >
      <TerminalBand model={model.contextBand} className="strategy-band" compact hideHint hideEyebrow />
      <div className="ws-actions">
        <button type="button" className="soft-button" onClick={() => onSelectWorkspace?.('execution')}>
          {t('workspace.cta.execution')}
        </button>
        <button type="button" className="soft-button" onClick={() => onSelectWorkspace?.('inference')}>
          {t('workspace.cta.inference')}
        </button>
      </div>
    </SectionFrame>
  )

  const operationsPanel = (
    <StrategyOrchestrationOperationsPanel
      model={model.operations.model}
      drafts={model.operations.drafts}
      reason={model.operations.reason}
      conflictPolicy={model.operations.conflictPolicy}
      downgradePolicy={model.operations.downgradePolicy}
      onReasonChange={model.operations.setReason}
      onConflictPolicyChange={model.operations.setConflictPolicy}
      onDowngradePolicyChange={model.operations.setDowngradePolicy}
      onDraftFieldChange={model.operations.setDraftField}
      onSaveEntry={(strategyId) => void model.operations.onSaveEntry(strategyId)}
      onSavePolicies={() => void model.operations.onSavePolicies()}
    />
  )

  if (panel === 'decision') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.strategy.title')}
        title={t('workspace.strategy.matrixTitle')}
        description={t('workspace.strategy.description')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
        actions={decisionActions}
        className="fwp-strategy-decision"
      >
        {decisionPanel}
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'registry') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.strategy.title')}
        title={t('workspace.strategy.registryTitle')}
        description={t('workspace.strategy.registryDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <SectionFrame
          title={t('workspace.strategy.registryTitle')}
          description={t('workspace.strategy.registryDescription')}
          descriptionMode="srOnly"
          accent="cyan"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
          <StrategyRegistryPanel model={model.strategyRegistry} />
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'operations') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.strategy.title')}
        title={t('workspace.strategy.operationsTitle')}
        description={t('workspace.strategy.operationsDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <SectionFrame
          title={t('workspace.strategy.operationsTitle')}
          description={t('workspace.strategy.operationsDescription')}
          descriptionMode="srOnly"
          accent="teal"
          stage="tail"
          compactHeader
          bodyClassName="tail-shell"
        >
          {operationsPanel}
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'audit') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.strategy.title')}
        title={t('workspace.strategy.auditTimelineTitle')}
        description={t('workspace.strategy.auditTimelineHint')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <SectionFrame
          title={t('workspace.strategy.auditTimelineTitle')}
          description={t('workspace.strategy.auditTimelineHint')}
          descriptionMode="srOnly"
          accent="amber"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
          <StrategyOrchestrationAuditTimeline model={model.strategyAuditTimeline} />
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  return (
    <div className="ws-grid ws-grid-strategy" data-workspace="strategy">
      <div className="workspace-home workspace-home-strategy">
        {homeSummaryPanel}
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
