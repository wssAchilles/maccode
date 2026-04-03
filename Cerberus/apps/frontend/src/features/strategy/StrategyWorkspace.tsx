import { useI18n } from '../../i18n/I18nProvider'
import type { WorkspaceId } from '../../store/slices/shared'
import {
  DiagnosticDrawer,
  SectionFrame,
  TerminalBand,
  WorkspaceOperatorDeck,
  WorkspaceSpotlight,
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
      <SectionFrame
        title={t('workspace.strategy.title')}
        description={t('workspace.strategy.description')}
        eyebrow={t('workspace.strategy.title')}
        className="ws-span-full"
        tone="hero"
        accent="teal"
        stage="hero"
      >
        <TerminalBand model={model.contextBand} className="hero-band" />
        <WorkspaceSpotlight model={model.spotlight} className="ws-hero-spotlight" />
      </SectionFrame>

      <div className="ws-main stack wsm">
        <SectionFrame
          title={t('workspace.strategy.operatorDeckTitle')}
          description={t('workspace.strategy.operatorDeckDescription')}
          accent="teal"
          stage="operator"
          compactHeader
          bodyClassName="operator-shell"
        >
          <WorkspaceOperatorDeck sections={model.operatorSections} layout="rail" />
        </SectionFrame>

        <SectionFrame
          title={t('workspace.strategy.matrixTitle')}
          description={t('workspace.strategy.description')}
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
          title={t('workspace.strategy.operationsTitle')}
          description={t('workspace.strategy.operationsDescription')}
          accent="teal"
          stage="tail"
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
        </SectionFrame>
      </div>

      <div className="ws-side stack wss">
        <SectionFrame
          title={t('workspace.strategy.registryTitle')}
          description={t('workspace.strategy.registryDescription')}
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
          accent="amber"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
          <StrategyOrchestrationAuditTimeline model={model.strategyAuditTimeline} />
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
