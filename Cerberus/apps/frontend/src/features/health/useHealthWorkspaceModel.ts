import { useMemo } from 'react'

import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import { buildInferenceDiagnosticsModel } from '../inference-observability/view-models'
import {
  buildHealthDiagnostics,
  buildHealthStoreItems,
  buildHealthWorkerItems,
} from './view-models'

export function useHealthWorkspaceModel() {
  const { t } = useI18n()
  const domainStatus = useCerberusStore((state) => state.uiState.domain_status)
  const persistenceStatus = useCerberusStore((state) => state.strategySummary.persistence_status)
  const inferenceStatus = useCerberusStore((state) => state.strategySummary.inference_status)
  const summaryError = useCerberusStore((state) => state.strategySummary.last_error)

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
    workerItems,
    storeItems,
    diagnostics,
    hasDiagnosticsAlert: Boolean(summaryError),
  }
}
