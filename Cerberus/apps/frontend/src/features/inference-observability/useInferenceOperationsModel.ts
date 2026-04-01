import { startTransition, useEffect, useMemo, useState } from 'react'
import { useShallow } from 'zustand/react/shallow'

import { formatAppError } from '../../lib/http'
import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import { useDormantSelector } from '../../store/useDormantSelector'
import { buildInferenceOperationsModel } from './view-models'

function inferActiveModelId(catalog: { active_model?: { model_id: string; version: string } | null } | undefined) {
  if (!catalog?.active_model) {
    return ''
  }
  return `${catalog.active_model.model_id}:${catalog.active_model.version}`
}

export function useInferenceOperationsModel(enabled = true) {
  const { t } = useI18n()
  const { inferenceStatus, inferenceCatalog, pendingAction, lastResult, lastError } = useDormantSelector(
    enabled,
    useShallow((state) => ({
      inferenceStatus: state.strategySummary.inference_status,
      inferenceCatalog: state.strategySummary.inference_catalog,
      pendingAction: state.strategySummary.inference_pending_action,
      lastResult: state.strategySummary.inference_last_result,
      lastError: state.strategySummary.last_error,
    })),
  )
  const loadInferenceCatalog = useCerberusStore((state) => state.strategySummaryActions.loadInferenceCatalog)
  const requestPromotion = useCerberusStore((state) => state.strategySummaryActions.requestInferencePromotion)
  const requestRollback = useCerberusStore((state) => state.strategySummaryActions.requestInferenceRollback)
  const activateInferenceModel = useCerberusStore((state) => state.strategySummaryActions.activateInferenceModel)

  const [reason, setReason] = useState('')
  const [selectedModelId, setSelectedModelId] = useState('')

  useEffect(() => {
    if (!enabled) {
      return
    }
    if (!inferenceCatalog) {
      void loadInferenceCatalog()
    }
  }, [enabled, inferenceCatalog, loadInferenceCatalog])

  useEffect(() => {
    if (!enabled) {
      return
    }
    const activeId = inferActiveModelId(inferenceCatalog)
    if (!activeId) {
      return
    }
    startTransition(() => {
      setSelectedModelId((current) => current || activeId)
    })
  }, [enabled, inferenceCatalog])

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
