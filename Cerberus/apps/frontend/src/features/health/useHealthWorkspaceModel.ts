import { useMemo } from 'react'

import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import {
  buildHealthDiagnostics,
  buildHealthStoreItems,
  buildHealthWorkerItems,
} from './view-models'

export function useHealthWorkspaceModel() {
  const { t } = useI18n()
  const domainStatus = useCerberusStore((state) => state.uiState.domain_status)
  const persistenceStatus = useCerberusStore((state) => state.strategySummary.persistence_status)
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

  return {
    domainStatus,
    persistenceStatus,
    workerItems,
    storeItems,
    diagnostics,
    hasDiagnosticsAlert: Boolean(summaryError),
  }
}
