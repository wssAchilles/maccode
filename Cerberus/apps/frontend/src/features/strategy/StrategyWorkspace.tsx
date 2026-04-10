import { useI18n } from '../../i18n/I18nProvider'
import type { WorkspaceId } from '../../store/slices/shared'
import {
  DiagnosticDrawer,
  SectionFrame,
  WorkspaceOperatorDeck,
} from '../../ui'
import { StrategyDecisionMatrix } from '../strategy-orchestration/components/StrategyDecisionMatrix'
import { StrategyOrchestrationAuditTimeline } from '../strategy-orchestration/components/StrategyOrchestrationAuditTimeline'
import { StrategyOrchestrationOperationsPanel } from '../strategy-orchestration/components/StrategyOrchestrationOperationsPanel'
import { StrategyRegistryPanel } from '../strategy-orchestration/components/StrategyRegistryPanel'
import { useStrategyWorkspaceModel } from './useStrategyWorkspaceModel'

type Props = {
  active?: boolean
  onSelectWorkspace?: (workspace: WorkspaceId) => void
}

export function StrategyWorkspace({ active = true, onSelectWorkspace }: Props) {
  const { t } = useI18n()
  const model = useStrategyWorkspaceModel({ active })

  return (
    <div className="ws-grid ws-grid-strategy" data-workspace="strategy">
      <div className="ws-main stack wsm">
        <SectionFrame
          title={t('workspace.strategy.matrixTitle')}
          description={t('workspace.strategy.description')}
          descriptionMode="srOnly"
          className="ws-primary-panel"
          accent="cyan"
          stage="feature"
        >
          <StrategyDecisionMatrix model={model.strategyMatrix} />
          <div className="ws-actions">
            <button type="button" className="soft-button" onClick={() => onSelectWorkspace?.('execution')}>
              {t('workspace.cta.execution')}
            </button>
            <button type="button" className="soft-button" onClick={() => onSelectWorkspace?.('inference')}>
              {t('workspace.cta.inference')}
            </button>
          </div>
        </SectionFrame>

        <SectionFrame
          title={t('workspace.strategy.operatorDeckTitle')}
          description={t('workspace.strategy.operatorDeckDescription')}
          descriptionMode="srOnly"
          accent="teal"
          stage="operator"
          compactHeader
          bodyClassName="operator-shell"
        >
          <WorkspaceOperatorDeck sections={model.operatorSections} layout="rail" />
        </SectionFrame>

        <SectionFrame
          title={t('workspace.strategy.operationsTitle')}
          description={t('workspace.strategy.operationsDescription')}
          descriptionMode="srOnly"
          accent="teal"
          stage="tail"
          compactHeader
        >
          <DiagnosticDrawer
            title={t('workspace.strategy.operationsTitle')}
            summary={t('workspace.strategy.operationsDescription')}
            contentClassName="tail-drawer"
          >
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
          </DiagnosticDrawer>
        </SectionFrame>
      </div>

      <div className="ws-side stack wss">
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

        <SectionFrame
          title={t('workspace.strategy.auditTimelineTitle')}
          description={t('workspace.strategy.auditTimelineHint')}
          descriptionMode="srOnly"
          accent="amber"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
          <DiagnosticDrawer
            title={t('workspace.strategy.auditTimelineTitle')}
            summary={t('workspace.strategy.auditTimelineHint')}
            contentClassName="tail-drawer"
          >
            <StrategyOrchestrationAuditTimeline model={model.strategyAuditTimeline} />
          </DiagnosticDrawer>
        </SectionFrame>

        {model.summaryError ? (
          <DiagnosticDrawer title={t('workspace.execution.diagnostics')} summary={model.summaryError.message}>
            <pre className="diagnostic-pre">{JSON.stringify(model.summaryError, null, 2)}</pre>
          </DiagnosticDrawer>
        ) : null}
      </div>
    </div>
  )
}
