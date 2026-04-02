import { useMemo } from 'react'
import { useShallow } from 'zustand/react/shallow'

import { useI18n } from '../../i18n/I18nProvider'
import { useDormantSelector } from '../../store/useDormantSelector'
import { buildInferenceDiagnosticsModel } from '../inference-observability/view-models'
import {
  buildHealthDiagnostics,
  buildHealthOperatorSections,
  buildHealthSpotlightModel,
  buildServiceHealthPanelModel,
  buildHealthStoreItems,
  buildHealthWorkerItems,
} from './view-models'

export function useHealthWorkspaceModel(active = true) {
  const { t } = useI18n()
  const { domainStatus, persistenceStatus, inferenceStatus, summaryError } = useDormantSelector(
    active,
    useShallow((state) => ({
      domainStatus: state.uiState.domain_status,
      persistenceStatus: state.strategySummary.persistence_status,
      inferenceStatus: state.strategySummary.inference_status,
      summaryError: state.strategySummary.last_error,
    })),
  )

  const model = useMemo(() => {
    const inferenceDiagnostics = buildInferenceDiagnosticsModel({ t, inferenceStatus })

    return {
      workerItems: buildHealthWorkerItems({ t, persistenceStatus }),
      storeItems: buildHealthStoreItems({ t, persistenceStatus }),
      diagnostics: buildHealthDiagnostics(summaryError, domainStatus),
      serviceHealthPanel: buildServiceHealthPanelModel({ t, domainStatus, persistenceStatus }),
      inferenceDiagnostics,
      operatorSections: buildHealthOperatorSections({
        t,
        domainStatus,
        persistenceStatus,
        inferenceStatus,
      }),
      spotlight: buildHealthSpotlightModel({
        t,
        domainStatus,
        persistenceStatus,
        inferenceStatus,
      }),
      hasDiagnosticsAlert: Boolean(summaryError),
    }
  }, [domainStatus, inferenceStatus, persistenceStatus, summaryError, t])

  return {
    domainStatus,
    persistenceStatus,
    ...model,
  }
}
