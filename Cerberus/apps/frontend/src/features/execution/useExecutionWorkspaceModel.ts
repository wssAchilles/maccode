import { useMemo } from 'react'
import { useShallow } from 'zustand/react/shallow'

import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import { useDormantSelector } from '../../store/useDormantSelector'
import {
  buildPreparedTradingSnapshot,
} from '../../view-models/workbench'
import { buildPreparedExecutionSelection } from './read-models'
import { buildMatchingOrderBookPanelModel } from '../../view-models/orderbook'
import {
  buildStrategyOrchestrationAuditTimelineModel,
  buildExecutionLifecyclePanelModel,
  buildStrategyDecisionMatrixModel,
  buildStrategyPortfolioPanelModel,
  buildStrategyRegistryPanelModel,
} from '../strategy-orchestration/view-models'
import { buildExecutionOperationsPanel, buildExecutionSpotlightModel } from './view-models'

type Params = {
  active: boolean
}

export function useExecutionWorkspaceModel({ active: _active = true }: Params) {
  const { t } = useI18n()
  const {
    selectedSymbol,
    latest,
    latestBySymbol,
    strategySignal,
    persistenceStatus,
    orchestrationStatus,
    orderbook,
    latestEvent,
    orderEvents,
    heartbeat,
    summaryError,
    tradingPolicy,
    binanceRule,
    executionStatus,
  } = useDormantSelector(
    _active,
    useShallow((state) => ({
      selectedSymbol: state.marketStream.selected_symbol,
      latest: state.marketStream.latest,
      latestBySymbol: state.marketStream.latest_by_symbol,
      strategySignal: state.strategySummary.signal,
      persistenceStatus: state.strategySummary.persistence_status,
      orchestrationStatus: state.strategySummary.orchestration_status,
      orderbook: state.strategySummary.matching_orderbook,
      latestEvent: state.executionTrading.latest_event,
      orderEvents: state.executionTrading.order_events,
      heartbeat: state.executionTrading.heartbeat,
      summaryError: state.strategySummary.last_error,
      tradingPolicy: state.executionTrading.trading_policy,
      binanceRule: state.executionTrading.binance_rule,
      executionStatus: state.uiState.domain_status['execution-trading'],
    })),
  )
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
  const setSelectedSymbol = useCerberusStore((state) => state.marketStreamActions.setSelectedSymbol)
  const syncExecutionFilters = useCerberusStore((state) => state.executionTradingActions.setFilters)
  const preparedExecutionSelection = useMemo(
    () => buildPreparedExecutionSelection(orderEvents, selectedSymbol),
    [orderEvents, selectedSymbol],
  )

  const model = useMemo(() => ({
    metricTiles: [
      {
        id: 'signal',
        label: t('strategy.signal'),
        value: tradingSnapshot.signalValue,
        hint: `${t('strategy.confidence')}: ${tradingSnapshot.confidenceValue}`,
        tone: 'accent' as const,
      },
      {
        id: 'best-bid',
        label: t('market.bestBid'),
        value: tradingSnapshot.bestBidValue,
        tone: 'positive' as const,
      },
      {
        id: 'best-ask',
        label: t('market.bestAsk'),
        value: tradingSnapshot.bestAskValue,
        tone: 'negative' as const,
      },
      {
        id: 'execution-stream',
        label: t('execution.timeline'),
        value: tradingSnapshot.feedbackValue ?? t('common.heartbeat'),
        hint: tradingSnapshot.feedbackAtValue,
      },
    ],
    lifecyclePanel: buildExecutionLifecyclePanelModel({
      t,
      signal: strategySignal,
      persistenceStatus,
      preparedSelection: preparedExecutionSelection,
      latestEventSummary: tradingSnapshot.feedbackValue ?? t('common.heartbeat'),
      heartbeat,
      tradingPolicy,
      binanceRule,
      domainStatus: executionStatus,
    }),
    operationsPanel: buildExecutionOperationsPanel({
      t,
      selectedSymbol,
      preparedSelection: preparedExecutionSelection,
      persistenceStatus,
      domainStatus: executionStatus,
    }),
    strategyMatrix: buildStrategyDecisionMatrixModel({ t, signal: strategySignal }),
    portfolioPanel: buildStrategyPortfolioPanelModel({ t, signal: strategySignal, selectedSymbol }),
    strategyRegistry: buildStrategyRegistryPanelModel({ t, signal: strategySignal, selectedSymbol, orchestrationStatus }),
    strategyAuditTimeline: buildStrategyOrchestrationAuditTimelineModel({ t, orchestrationStatus }),
    orderbookPanel: buildMatchingOrderBookPanelModel({ t, orderbook }),
    spotlight: buildExecutionSpotlightModel({
      t,
      snapshot: tradingSnapshot,
      preparedSelection: preparedExecutionSelection,
      tradingPolicy,
      binanceRule,
    }),
  }), [
    binanceRule,
    executionStatus,
    heartbeat,
    orchestrationStatus,
    orderbook,
    persistenceStatus,
    preparedExecutionSelection,
    selectedSymbol,
    strategySignal,
    t,
    tradingPolicy,
    tradingSnapshot,
  ])

  const selectSymbol = (symbol: string) => {
    setSelectedSymbol(symbol)
    syncExecutionFilters({ symbol })
  }

  return {
    selectedSymbol,
    selectSymbol,
    displayQuote: tradingSnapshot.displayQuote,
    summaryError,
    ...model,
  }
}
