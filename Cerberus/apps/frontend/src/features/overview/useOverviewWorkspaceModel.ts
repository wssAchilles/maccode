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
  buildOverviewContextBandModel,
  buildOverviewHealthDigestBandModel,
  buildOverviewInferenceBandModel,
  buildOverviewMetricTiles,
  buildOverviewOperatorSections,
  buildOverviewRecentSignalCards,
  buildOverviewSpotlightModel,
  buildOverviewTailBandModel,
  buildOverviewPersistenceItems,
} from './view-models'
import { buildInferenceStatusCardModel } from '../inference-observability/view-models'
import {
  buildStrategyOrchestrationAuditTimelineModel,
  buildStrategyContextBandModel,
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

  const model = useMemo(() => {
    const domainSummary = summarizeDomainStates(domainStatus)
    const persistenceItems = buildOverviewPersistenceItems({ t, persistenceStatus })
    const inferenceCard = buildInferenceStatusCardModel({ t, inferenceStatus })

    return {
      metricTiles: buildOverviewMetricTiles({
        t,
        snapshot: tradingSnapshot,
      }),
      healthCards: buildHealthCards(domainStatus, t),
      persistenceItems,
      inferenceCard,
      strategyMatrix: buildStrategyDecisionMatrixModel({ t, signal: strategySignal }),
      portfolioPanel: buildStrategyPortfolioPanelModel({ t, signal: strategySignal, selectedSymbol }),
      strategyRegistry: buildStrategyRegistryPanelModel({ t, signal: strategySignal, selectedSymbol, orchestrationStatus }),
      strategyAuditTimeline: buildStrategyOrchestrationAuditTimelineModel({ t, orchestrationStatus }),
      strategyBand: buildStrategyContextBandModel({ t, signal: strategySignal, selectedSymbol, orchestrationStatus }),
      recentSignals: buildOverviewRecentSignalCards({ t, recentSignals }),
      contextBand: buildOverviewContextBandModel({
        t,
        snapshot: tradingSnapshot,
        readyCount: domainSummary.readyCount,
        attentionCount: domainSummary.attentionCount,
      }),
      operatorSections: buildOverviewOperatorSections({
        t,
        snapshot: tradingSnapshot,
        readyCount: domainSummary.readyCount,
        attentionCount: domainSummary.attentionCount,
        recentSignalCount: recentSignals.length,
      }),
      healthDigestBand: buildOverviewHealthDigestBandModel({
        t,
        domainStatus,
      }),
      inferenceBand: buildOverviewInferenceBandModel({
        t,
        inferenceCard,
      }),
      tailBand: buildOverviewTailBandModel({
        t,
        snapshot: tradingSnapshot,
        recentSignalCount: recentSignals.length,
        persistenceItems,
      }),
      spotlight: buildOverviewSpotlightModel({
        t,
        snapshot: tradingSnapshot,
        readyCount: domainSummary.readyCount,
        attentionCount: domainSummary.attentionCount,
      }),
    }
  }, [
    domainStatus,
    inferenceStatus,
    orchestrationStatus,
    persistenceStatus,
    recentSignals,
    selectedSymbol,
    strategySignal,
    t,
    tradingSnapshot,
  ])

  const selectSymbol = (symbol: string) => {
    setSelectedSymbol(symbol)
    syncExecutionFilters({ symbol })
  }

  return {
    summaryError,
    ...model,
    selectSymbol,
    openExecution: () => onSelectWorkspace('execution'),
    openHealth: () => onSelectWorkspace('health'),
    openMarket: () => onSelectWorkspace('market'),
  }
}
