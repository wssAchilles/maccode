import { useMemo } from 'react'

import { useCandlesResource } from '../../app/bootstrap/useResourceQueries'
import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import {
  buildStrategyRegistryPanelModel,
  buildStrategyDecisionMatrixModel,
  buildStrategyPortfolioPanelModel,
} from '../strategy-orchestration/view-models'
import {
  buildMarketChartStateModel,
  buildMarketChartMarkersModel,
  buildMarketExecutionRailModel,
  buildMarketMetricTiles,
  buildMarketSymbolChips,
} from './view-models'

type Params = {
  active: boolean
}

export function useMarketWorkspaceModel({ active }: Params) {
  const { t } = useI18n()
  const selectedSymbol = useCerberusStore((state) => state.marketStream.selected_symbol)
  const latest = useCerberusStore((state) => state.marketStream.latest)
  const latestBySymbol = useCerberusStore((state) => state.marketStream.latest_by_symbol)
  const latestEvent = useCerberusStore((state) => state.executionTrading.latest_event)
  const orderEvents = useCerberusStore((state) => state.executionTrading.order_events)
  const candles = useCerberusStore((state) => state.marketStream.candles)
  const marketStatus = useCerberusStore((state) => state.uiState.domain_status['market-stream'])
  const summaryError = useCerberusStore((state) => state.strategySummary.last_error)
  const strategySignal = useCerberusStore((state) => state.strategySummary.signal)
  const orderbook = useCerberusStore((state) => state.strategySummary.matching_orderbook)
  const setSelectedSymbol = useCerberusStore((state) => state.marketStreamActions.setSelectedSymbol)
  const syncExecutionFilters = useCerberusStore((state) => state.executionTradingActions.setFilters)

  const candlesQuery = useCandlesResource(active)

  const displayQuote = latestBySymbol[selectedSymbol] ?? latest

  const symbolChips = useMemo(
    () => buildMarketSymbolChips(selectedSymbol),
    [selectedSymbol],
  )

  const metricTiles = useMemo(
    () =>
      buildMarketMetricTiles({
        t,
        displayQuote,
        strategySignal,
        latestEvent,
      }),
    [displayQuote, latestEvent, strategySignal, t],
  )

  const chartState = useMemo(
    () =>
      buildMarketChartStateModel({
        t,
        candlesCount: candles.length,
        candlesFetching: candlesQuery.isLoading || candlesQuery.isFetching,
        marketStatus,
      }),
    [candles.length, candlesQuery.isFetching, candlesQuery.isLoading, marketStatus, t],
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
    () => buildStrategyRegistryPanelModel({ t, signal: strategySignal, selectedSymbol }),
    [selectedSymbol, strategySignal, t],
  )

  const executionRail = useMemo(
    () => buildMarketExecutionRailModel({ t, orderEvents, selectedSymbol }),
    [orderEvents, selectedSymbol, t],
  )

  const chartMarkers = useMemo(
    () => buildMarketChartMarkersModel({ orderEvents, selectedSymbol }),
    [orderEvents, selectedSymbol],
  )

  const selectSymbol = (symbol: string) => {
    setSelectedSymbol(symbol)
    syncExecutionFilters({ symbol })
  }

  return {
    activeSymbol: selectedSymbol,
    candles,
    chartMarkers,
    chartState,
    summaryError,
    orderbook,
    symbolChips,
    metricTiles,
    portfolioPanel,
    strategyRegistry,
    strategyMatrix,
    executionRail,
    selectSymbol,
  }
}
