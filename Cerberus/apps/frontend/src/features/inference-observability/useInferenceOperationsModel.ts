import { startTransition, useEffect, useMemo, useState } from 'react'

import { formatAppError } from '../../lib/http'
import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import { buildInferenceOperationsModel } from './view-models'

function inferActiveModelId(catalog: { active_model?: { model_id: string; version: string } | null } | undefined) {
  if (!catalog?.active_model) {
    return ''
  }
  return `${catalog.active_model.model_id}:${catalog.active_model.version}`
}

export function useInferenceOperationsModel() {
  const { t } = useI18n()
  const inferenceStatus = useCerberusStore((state) => state.strategySummary.inference_status)
  const inferenceCatalog = useCerberusStore((state) => state.strategySummary.inference_catalog)
  const pendingAction = useCerberusStore((state) => state.strategySummary.inference_pending_action)
  const lastResult = useCerberusStore((state) => state.strategySummary.inference_last_result)
  const lastError = useCerberusStore((state) => state.strategySummary.last_error)
  const loadInferenceCatalog = useCerberusStore((state) => state.strategySummaryActions.loadInferenceCatalog)
  const requestPromotion = useCerberusStore((state) => state.strategySummaryActions.requestInferencePromotion)
  const requestRollback = useCerberusStore((state) => state.strategySummaryActions.requestInferenceRollback)
  const activateInferenceModel = useCerberusStore((state) => state.strategySummaryActions.activateInferenceModel)

  const [reason, setReason] = useState('')
  const [selectedModelId, setSelectedModelId] = useState('')

  useEffect(() => {
    if (!inferenceCatalog) {
      void loadInferenceCatalog()
    }
  }, [inferenceCatalog, loadInferenceCatalog])

  useEffect(() => {
    const activeId = inferActiveModelId(inferenceCatalog)
    if (!activeId) {
      return
    }
    startTransition(() => {
      setSelectedModelId((current) => current || activeId)
    })
  }, [inferenceCatalog])

  const baseModel = useMemo(
    () =>
      buildInferenceOperationsModel({
        t,
        inferenceStatus,
        catalog: inferenceCatalog,
        lastResult,
        selectedModelId,
      }),
    [inferenceCatalog, inferenceStatus, lastResult, selectedModelId, t],
  )

  const model = useMemo(
    () => ({
      ...baseModel,
      pendingAction: pendingAction ?? undefined,
      statusMessage: baseModel.statusMessage ?? (lastError ? formatAppError(lastError) : undefined),
      statusTone: baseModel.statusTone ?? (lastError ? 'danger' : undefined),
      canPromote: baseModel.canPromote && !pendingAction,
      canRollback: baseModel.canRollback && !pendingAction,
      canActivateModel: baseModel.canActivateModel && !pendingAction,
    }),
    [baseModel, lastError, pendingAction],
  )

  return {
    model,
    reason,
    setReason,
    selectedModelId,
    setSelectedModelId,
    onPromote: async () => {
      await requestPromotion(reason)
    },
    onRollback: async () => {
      await requestRollback(reason)
    },
    onActivate: async () => {
      const [modelId, version] = selectedModelId.split(':')
      if (!modelId) {
        return
      }
      await activateInferenceModel(modelId, version || undefined, reason)
    },
  }
}
