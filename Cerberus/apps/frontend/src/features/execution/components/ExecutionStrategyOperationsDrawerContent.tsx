import { StrategyOrchestrationOperationsPanel } from '../../strategy-orchestration/components/StrategyOrchestrationOperationsPanel'
import { useStrategyOrchestrationOperationsModel } from '../../strategy-orchestration/useStrategyOrchestrationOperationsModel'

export function ExecutionStrategyOperationsDrawerContent({ active }: { active: boolean }) {
  const orchestrationOps = useStrategyOrchestrationOperationsModel(active)

  return (
    <StrategyOrchestrationOperationsPanel
      model={orchestrationOps.model}
      drafts={orchestrationOps.drafts}
      reason={orchestrationOps.reason}
      conflictPolicy={orchestrationOps.conflictPolicy}
      downgradePolicy={orchestrationOps.downgradePolicy}
      onReasonChange={orchestrationOps.setReason}
      onConflictPolicyChange={orchestrationOps.setConflictPolicy}
      onDowngradePolicyChange={orchestrationOps.setDowngradePolicy}
      onDraftFieldChange={orchestrationOps.setDraftField}
      onSaveEntry={orchestrationOps.onSaveEntry}
      onSavePolicies={orchestrationOps.onSavePolicies}
    />
  )
}
