import { InferenceOperationsPanel } from '../inference-observability/components/InferenceOperationsPanel'
import { useInferenceOperationsModel } from '../inference-observability/useInferenceOperationsModel'

export function HealthInferenceOperationsDrawerContent({ active }: { active: boolean }) {
  const inferenceOperations = useInferenceOperationsModel(active)

  return (
    <InferenceOperationsPanel
      model={inferenceOperations.model}
      reason={inferenceOperations.reason}
      selectedModelId={inferenceOperations.selectedModelId}
      onReasonChange={inferenceOperations.setReason}
      onSelectedModelIdChange={inferenceOperations.setSelectedModelId}
      onPromote={inferenceOperations.onPromote}
      onRollback={inferenceOperations.onRollback}
      onActivate={inferenceOperations.onActivate}
    />
  )
}
