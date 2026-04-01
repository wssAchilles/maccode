import { useMemo } from 'react'
import { useShallow } from 'zustand/react/shallow'

import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import { useDormantSelector } from '../../store/useDormantSelector'
import type { WorkspaceId } from '../../store/slices/shared'
import {
  buildPreparedTradingSnapshot,
  buildHealthCards,
  summarizeDomainStates,
} from '../../view-models/workbench'
import {
  buildOverviewMetricTiles,
  buildOverviewSpotlightModel,
  buildOverviewPersistenceItems,
} from './view-models'
import { buildInferenceStatusCardModel } from '../inference-observability/view-models'
import {
  buildStrategyOrchestrationAuditTimelineModel,
  buildStrategyDecisionMatrixModel,
  buildStrategyPortfolioPanelModel,
  buildStrategyRegistryPanelModel,
} from '../strategy-orchestration/view-models'

type Params = {
  active: boolean
  onSelectWorkspace: (workspace: WorkspaceId) => void
}

export function useOverviewWorkspaceModel({ active, onSelectWorkspace }: Params) {
  const { t } = useI18n()
  const {
    selectedSymbol,
    latest,
    latestBySymbol,
    strategySignal,
    recentSignals,
    persistenceStatus,
    inferenceStatus,
    orchestrationStatus,
    summaryError,
    latestEvent,
    heartbeat,
    domainStatus,
  } = useDormantSelector(
    active,
    useShallow((state) => ({
      selectedSymbol: state.marketStream.selected_symbol,
      latest: state.marketStream.latest,
      latestBySymbol: state.marketStream.latest_by_symbol,
      strategySignal: state.strategySummary.signal,
      recentSignals: state.strategySummary.recent_signals,
      persistenceStatus: state.strategySummary.persistence_status,
      inferenceStatus: state.strategySummary.inference_status,
      orchestrationStatus: state.strategySummary.orchestration_status,
      summaryError: state.strategySummary.last_error,
      latestEvent: state.executionTrading.latest_event,
      heartbeat: state.executionTrading.heartbeat,
      domainStatus: state.uiState.domain_status,
    })),
  )
  const setSelectedSymbol = useCerberusStore((state) => state.marketStreamActions.setSelectedSymbol)
  const syncExecutionFilters = useCerberusStore((state) => state.executionTradingActions.setFilters)

  const tradingSnapshot = useMemo(
    () =>
      buildPreparedTradingSnapshot({
        selectedSymbol,
        latest,
        latestBySymbol,
        strategySignal,
        latestEvent,
        heartbeat,
      }),
    [heartbeat, latest, latestBySymbol, latestEvent, selectedSymbol, strategySignal],
  )

  const metricTiles = useMemo(
    () =>
      buildOverviewMetricTiles({
        t,
        snapshot: tradingSnapshot,
      }),
    [t, tradingSnapshot],
  )

  const healthCards = useMemo(() => buildHealthCards(domainStatus, t), [domainStatus, t])
  const domainSummary = useMemo(() => summarizeDomainStates(domainStatus), [domainStatus])

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

  const strategyRegistry = useMemo(
    () => buildStrategyRegistryPanelModel({ t, signal: strategySignal, selectedSymbol, orchestrationStatus }),
    [orchestrationStatus, selectedSymbol, strategySignal, t],
  )

  const strategyAuditTimeline = useMemo(
    () => buildStrategyOrchestrationAuditTimelineModel({ t, orchestrationStatus }),
    [orchestrationStatus, t],
  )
  const recentSignalRows = useMemo(() => recentSignals.slice(0, 4), [recentSignals])

  const spotlight = useMemo(
    () =>
      buildOverviewSpotlightModel({
        t,
        snapshot: tradingSnapshot,
        readyCount: domainSummary.readyCount,
        attentionCount: domainSummary.attentionCount,
      }),
    [domainSummary.attentionCount, domainSummary.readyCount, t, tradingSnapshot],
  )

  const selectSymbol = (symbol: string) => {
    setSelectedSymbol(symbol)
    syncExecutionFilters({ symbol })
  }

  return {
    summaryError,
    healthCards,
    inferenceCard,
    strategyMatrix,
    portfolioPanel,
    strategyRegistry,
    strategyAuditTimeline,
    metricTiles,
    spotlight,
    persistenceItems,
    recentSignals: recentSignalRows,
    selectSymbol,
    openExecution: () => onSelectWorkspace('execution'),
    openHealth: () => onSelectWorkspace('health'),
    openMarket: () => onSelectWorkspace('market'),
  }
}
