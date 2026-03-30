import { useMemo } from 'react'

import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import {
  formatConfidence,
  summarizeLatestEventAt,
  summarizeLatestFeedback,
} from '../../view-models/workbench'
import {
  buildExecutionLifecyclePanelModel,
  buildStrategyDecisionMatrixModel,
  buildStrategyPortfolioPanelModel,
} from '../strategy-orchestration/view-models'

type Params = {
  active: boolean
}

export function useExecutionWorkspaceModel({ active: _active = true }: Params) {
  const { t } = useI18n()
  const selectedSymbol = useCerberusStore((state) => state.marketStream.selected_symbol)
  const latest = useCerberusStore((state) => state.marketStream.latest)
  const latestBySymbol = useCerberusStore((state) => state.marketStream.latest_by_symbol)
  const strategySignal = useCerberusStore((state) => state.strategySummary.signal)
  const persistenceStatus = useCerberusStore((state) => state.strategySummary.persistence_status)
  const orderbook = useCerberusStore((state) => state.strategySummary.matching_orderbook)
  const latestEvent = useCerberusStore((state) => state.executionTrading.latest_event)
  const heartbeat = useCerberusStore((state) => state.executionTrading.heartbeat)
  const summaryError = useCerberusStore((state) => state.strategySummary.last_error)
  const tradingPolicy = useCerberusStore((state) => state.executionTrading.trading_policy)
  const binanceRule = useCerberusStore((state) => state.executionTrading.binance_rule)
  const executionStatus = useCerberusStore((state) => state.uiState.domain_status['execution-trading'])

  const displayQuote = latestBySymbol[selectedSymbol] ?? latest
  const setSelectedSymbol = useCerberusStore((state) => state.marketStreamActions.setSelectedSymbol)

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
        latestEventSummary: summarizeLatestFeedback(latestEvent, heartbeat, t),
        heartbeat,
        tradingPolicy,
        binanceRule,
        domainStatus: executionStatus,
      }),
    [binanceRule, executionStatus, heartbeat, latestEvent, persistenceStatus, strategySignal, t, tradingPolicy],
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
    selectedSymbol,
    selectSymbol: setSelectedSymbol,
    displayQuote,
    orderbook,
    summaryError,
    metricTiles,
    lifecyclePanel,
    strategyMatrix,
    portfolioPanel,
  }
}
