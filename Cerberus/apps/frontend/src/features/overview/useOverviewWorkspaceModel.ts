import { useMemo } from 'react'

import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import type { WorkspaceId } from '../../store/slices/shared'
import {
  buildHealthCards,
} from '../../view-models/workbench'
import {
  buildOverviewMetricTiles,
  buildOverviewPersistenceItems,
} from './view-models'
import { buildInferenceStatusCardModel } from '../inference-observability/view-models'
import {
  buildStrategyDecisionMatrixModel,
  buildStrategyPortfolioPanelModel,
} from '../strategy-orchestration/view-models'

type Params = {
  onSelectWorkspace: (workspace: WorkspaceId) => void
}

export function useOverviewWorkspaceModel({ onSelectWorkspace }: Params) {
  const { t } = useI18n()
  const selectedSymbol = useCerberusStore((state) => state.marketStream.selected_symbol)
  const latest = useCerberusStore((state) => state.marketStream.latest)
  const latestBySymbol = useCerberusStore((state) => state.marketStream.latest_by_symbol)
  const strategySignal = useCerberusStore((state) => state.strategySummary.signal)
  const recentSignals = useCerberusStore((state) => state.strategySummary.recent_signals)
  const persistenceStatus = useCerberusStore((state) => state.strategySummary.persistence_status)
  const inferenceStatus = useCerberusStore((state) => state.strategySummary.inference_status)
  const summaryError = useCerberusStore((state) => state.strategySummary.last_error)
  const latestEvent = useCerberusStore((state) => state.executionTrading.latest_event)
  const heartbeat = useCerberusStore((state) => state.executionTrading.heartbeat)
  const domainStatus = useCerberusStore((state) => state.uiState.domain_status)
  const setSelectedSymbol = useCerberusStore((state) => state.marketStreamActions.setSelectedSymbol)

  const displayQuote = latestBySymbol[selectedSymbol] ?? latest

  const metricTiles = useMemo(
    () =>
      buildOverviewMetricTiles({
        t,
        selectedSymbol,
        displayQuote,
        strategySignal,
        latestEvent,
        heartbeat,
      }),
    [displayQuote, heartbeat, latestEvent, selectedSymbol, strategySignal, t],
  )

  const healthCards = useMemo(() => buildHealthCards(domainStatus, t), [domainStatus, t])

  const persistenceItems = useMemo(
    () => buildOverviewPersistenceItems({ t, persistenceStatus }),
    [persistenceStatus, t],
  )

  const inferenceCard = useMemo(
    () => buildInferenceStatusCardModel({ t, inferenceStatus }),
    [inferenceStatus, t],
  )

  const strategyMatrix = useMemo(
    () => buildStrategyDecisionMatrixModel({ t, signal: strategySignal }),
    [strategySignal, t],
  )

  const portfolioPanel = useMemo(
    () => buildStrategyPortfolioPanelModel({ t, signal: strategySignal, selectedSymbol }),
    [selectedSymbol, strategySignal, t],
  )

  return {
    summaryError,
    healthCards,
    inferenceCard,
    strategyMatrix,
    portfolioPanel,
    metricTiles,
    persistenceItems,
    recentSignals: recentSignals.slice(0, 4),
    selectSymbol: setSelectedSymbol,
    openExecution: () => onSelectWorkspace('execution'),
    openHealth: () => onSelectWorkspace('health'),
    openMarket: () => onSelectWorkspace('market'),
  }
}
