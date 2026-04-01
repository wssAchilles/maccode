import { useMemo } from 'react'
import { useShallow } from 'zustand/react/shallow'

import { useI18n } from '../../i18n/I18nProvider'
import { useDormantSelector } from '../../store/useDormantSelector'
import { useInferenceOperationsModel } from '../inference-observability/useInferenceOperationsModel'
import { buildInferenceDiagnosticsModel } from '../inference-observability/view-models'
import {
  buildHealthDiagnostics,
  buildServiceHealthPanelModel,
  buildHealthStoreItems,
  buildHealthWorkerItems,
} from './view-models'

export function useHealthWorkspaceModel(active = true) {
  const { t } = useI18n()
  const inferenceOperations = useInferenceOperationsModel(active)
  const { domainStatus, persistenceStatus, inferenceStatus, summaryError } = useDormantSelector(
    active,
    useShallow((state) => ({
      domainStatus: state.uiState.domain_status,
      persistenceStatus: state.strategySummary.persistence_status,
      inferenceStatus: state.strategySummary.inference_status,
      summaryError: state.strategySummary.last_error,
    })),
  )

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

  const serviceHealthPanel = useMemo(
    () => buildServiceHealthPanelModel({ t, domainStatus, persistenceStatus }),
    [domainStatus, persistenceStatus, t],
  )

  const inferenceDiagnostics = useMemo(
    () => buildInferenceDiagnosticsModel({ t, inferenceStatus }),
    [inferenceStatus, t],
  )

  return {
    domainStatus,
    persistenceStatus,
    serviceHealthPanel,
    inferenceDiagnostics,
    inferenceOperations,
    workerItems,
    storeItems,
    diagnostics,
    hasDiagnosticsAlert: Boolean(summaryError),
  }
}
