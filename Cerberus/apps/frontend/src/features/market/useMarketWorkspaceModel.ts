import { useMemo } from 'react'
import { useShallow } from 'zustand/react/shallow'

import { useCandlesResource } from '../../app/bootstrap/useResourceQueries'
import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import { useDormantSelector } from '../../store/useDormantSelector'
import { buildMatchingOrderBookPanelModel } from '../../view-models/orderbook'
import { buildPreparedTradingSnapshot } from '../../view-models/workbench'
import { buildPreparedExecutionSelection } from '../execution/read-models'
import {
  buildStrategyRegistryPanelModel,
  buildStrategyDecisionMatrixModel,
  buildStrategyPortfolioPanelModel,
} from '../strategy-orchestration/view-models'
import {
  buildMarketChartStateModel,
  buildMarketChartSeriesModel,
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
  const {
    selectedSymbol,
    latest,
    latestBySymbol,
    latestEvent,
    orderEvents,
    candles,
    marketStatus,
    summaryError,
    strategySignal,
    orchestrationStatus,
    orderbook,
  } = useDormantSelector(
    active,
    useShallow((state) => ({
      selectedSymbol: state.marketStream.selected_symbol,
      latest: state.marketStream.latest,
      latestBySymbol: state.marketStream.latest_by_symbol,
      latestEvent: state.executionTrading.latest_event,
      orderEvents: state.executionTrading.order_events,
      candles: state.marketStream.candles,
      marketStatus: state.uiState.domain_status['market-stream'],
      summaryError: state.strategySummary.last_error,
      strategySignal: state.strategySummary.signal,
      orchestrationStatus: state.strategySummary.orchestration_status,
      orderbook: state.strategySummary.matching_orderbook,
    })),
  )
  const setSelectedSymbol = useCerberusStore((state) => state.marketStreamActions.setSelectedSymbol)
  const syncExecutionFilters = useCerberusStore((state) => state.executionTradingActions.setFilters)

  const candlesQuery = useCandlesResource(active)
  const preparedExecutionSelection = useMemo(
    () => buildPreparedExecutionSelection(orderEvents, selectedSymbol),
    [orderEvents, selectedSymbol],
  )

  const tradingSnapshot = useMemo(
    () =>
      buildPreparedTradingSnapshot({
        selectedSymbol,
        latest,
        latestBySymbol,
        strategySignal,
        latestEvent,
      }),
    [latest, latestBySymbol, latestEvent, selectedSymbol, strategySignal],
  )

  const symbolChips = useMemo(
    () => buildMarketSymbolChips(selectedSymbol),
    [selectedSymbol],
  )

  const metricTiles = useMemo(
    () =>
      buildMarketMetricTiles({
        t,
        snapshot: tradingSnapshot,
      }),
    [t, tradingSnapshot],
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

  const chartSeries = useMemo(
    () => buildMarketChartSeriesModel(candles),
    [candles],
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

  const executionRail = useMemo(
    () => buildMarketExecutionRailModel({ t, selectedSymbol, preparedSelection: preparedExecutionSelection }),
    [preparedExecutionSelection, selectedSymbol, t],
  )

  const chartMarkers = useMemo(
    () => buildMarketChartMarkersModel({ orderEvents, selectedSymbol }),
    [orderEvents, selectedSymbol],
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
    activeSymbol: selectedSymbol,
    chartSeries,
    chartMarkers,
    chartState,
    summaryError,
    orderbookPanel,
    symbolChips,
    metricTiles,
    portfolioPanel,
    strategyRegistry,
    strategyMatrix,
    executionRail,
    selectSymbol,
  }
}
