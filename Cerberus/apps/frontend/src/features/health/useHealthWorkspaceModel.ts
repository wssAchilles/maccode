import { useMemo } from 'react'

import { useI18n } from '../../i18n/I18nProvider'
import { useDormantSelector } from '../../store/useDormantSelector'
import { useInferenceOperationsModel } from '../inference-observability/useInferenceOperationsModel'
import { buildInferenceDiagnosticsModel } from '../inference-observability/view-models'
import {
  buildHealthDiagnostics,
  buildHealthStoreItems,
  buildHealthWorkerItems,
} from './view-models'

export function useHealthWorkspaceModel(active = true) {
  const { t } = useI18n()
  const inferenceOperations = useInferenceOperationsModel(active)
  const domainStatus = useDormantSelector(active, (state) => state.uiState.domain_status)
  const persistenceStatus = useDormantSelector(active, (state) => state.strategySummary.persistence_status)
  const inferenceStatus = useDormantSelector(active, (state) => state.strategySummary.inference_status)
  const summaryError = useDormantSelector(active, (state) => state.strategySummary.last_error)

  const workerItems = useMemo(
    () => buildHealthWorkerItems({ t, persistenceStatus }),
    [persistenceStatus, t],
  )

  const storeItems = useMemo(
    () => buildHealthStoreItems({ t, persistenceStatus }),
    [persistenceStatus, t],
  )

  const diagnostics = useMemo(
    () => buildHealthDiagnostics(summaryError, domainStatus),
    [domainStatus, summaryError],
  )

  const inferenceDiagnostics = useMemo(
    () => buildInferenceDiagnosticsModel({ t, inferenceStatus }),
    [inferenceStatus, t],
  )

  return {
    domainStatus,
    persistenceStatus,
    inferenceDiagnostics,
    inferenceOperations,
    workerItems,
    storeItems,
    diagnostics,
    hasDiagnosticsAlert: Boolean(summaryError),
  }
}
