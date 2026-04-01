import { useMemo } from 'react'

import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import { useDormantSelector } from '../../store/useDormantSelector'
import {
  formatConfidence,
  summarizeLatestEventAt,
  summarizeLatestFeedback,
} from '../../view-models/workbench'
import { buildMatchingOrderBookPanelModel } from '../../view-models/orderbook'
import {
  buildStrategyOrchestrationAuditTimelineModel,
  buildExecutionLifecyclePanelModel,
  buildStrategyDecisionMatrixModel,
  buildStrategyPortfolioPanelModel,
  buildStrategyRegistryPanelModel,
} from '../strategy-orchestration/view-models'
import { buildExecutionOperationsPanel } from './view-models'

type Params = {
  active: boolean
}

export function useExecutionWorkspaceModel({ active: _active = true }: Params) {
  const { t } = useI18n()
  const selectedSymbol = useDormantSelector(_active, (state) => state.marketStream.selected_symbol)
  const latest = useDormantSelector(_active, (state) => state.marketStream.latest)
  const latestBySymbol = useDormantSelector(_active, (state) => state.marketStream.latest_by_symbol)
  const strategySignal = useDormantSelector(_active, (state) => state.strategySummary.signal)
  const persistenceStatus = useDormantSelector(_active, (state) => state.strategySummary.persistence_status)
  const orchestrationStatus = useDormantSelector(_active, (state) => state.strategySummary.orchestration_status)
  const orderbook = useDormantSelector(_active, (state) => state.strategySummary.matching_orderbook)
  const latestEvent = useDormantSelector(_active, (state) => state.executionTrading.latest_event)
  const orderEvents = useDormantSelector(_active, (state) => state.executionTrading.order_events)
  const heartbeat = useDormantSelector(_active, (state) => state.executionTrading.heartbeat)
  const summaryError = useDormantSelector(_active, (state) => state.strategySummary.last_error)
  const tradingPolicy = useDormantSelector(_active, (state) => state.executionTrading.trading_policy)
  const binanceRule = useDormantSelector(_active, (state) => state.executionTrading.binance_rule)
  const executionStatus = useDormantSelector(_active, (state) => state.uiState.domain_status['execution-trading'])

  const displayQuote = latestBySymbol[selectedSymbol] ?? latest
  const setSelectedSymbol = useCerberusStore((state) => state.marketStreamActions.setSelectedSymbol)
  const syncExecutionFilters = useCerberusStore((state) => state.executionTradingActions.setFilters)

  const metricTiles = useMemo(
    () => [
      {
        id: 'signal',
        label: t('strategy.signal'),
        value: strategySignal?.signal ?? 'HOLD',
        hint: `${t('strategy.confidence')}: ${formatConfidence(strategySignal?.confidence)}`,
        tone: 'accent' as const,
      },
      {
        id: 'best-bid',
        label: t('market.bestBid'),
        value: displayQuote?.bid_price ?? '—',
        tone: 'positive' as const,
      },
      {
        id: 'best-ask',
        label: t('market.bestAsk'),
        value: displayQuote?.ask_price ?? '—',
        tone: 'negative' as const,
      },
      {
        id: 'execution-stream',
        label: t('execution.timeline'),
        value: summarizeLatestFeedback(latestEvent, heartbeat, t),
        hint: summarizeLatestEventAt(latestEvent),
      },
    ],
    [displayQuote?.ask_price, displayQuote?.bid_price, heartbeat, latestEvent, strategySignal?.confidence, strategySignal?.signal, t],
  )

  const lifecyclePanel = useMemo(
    () =>
      buildExecutionLifecyclePanelModel({
        t,
        signal: strategySignal,
        persistenceStatus,
        orderEvents,
        selectedSymbol,
        latestEventSummary: summarizeLatestFeedback(latestEvent, heartbeat, t),
        heartbeat,
        tradingPolicy,
        binanceRule,
        domainStatus: executionStatus,
      }),
    [binanceRule, executionStatus, heartbeat, latestEvent, orderEvents, persistenceStatus, selectedSymbol, strategySignal, t, tradingPolicy],
  )

  const operationsPanel = useMemo(
    () =>
      buildExecutionOperationsPanel({
        t,
        selectedSymbol,
        orderEvents,
        persistenceStatus,
        domainStatus: executionStatus,
      }),
    [executionStatus, orderEvents, persistenceStatus, selectedSymbol, t],
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

  const orderbookPanel = useMemo(
    () => buildMatchingOrderBookPanelModel({ t, orderbook }),
    [orderbook, t],
  )

  const selectSymbol = (symbol: string) => {
    setSelectedSymbol(symbol)
    syncExecutionFilters({ symbol })
  }

  return {
    selectedSymbol,
    selectSymbol,
    displayQuote,
    orderbookPanel,
    summaryError,
    metricTiles,
    lifecyclePanel,
    operationsPanel,
    strategyMatrix,
    portfolioPanel,
    strategyRegistry,
    strategyAuditTimeline,
  }
}
