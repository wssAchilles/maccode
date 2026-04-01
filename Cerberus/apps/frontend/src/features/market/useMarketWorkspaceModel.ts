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
  buildMarketSpotlightModel,
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

  const model = useMemo(() => {
    const orderbookPanel = buildMatchingOrderBookPanelModel({ t, orderbook })
    const executionRail = buildMarketExecutionRailModel({
      t,
      selectedSymbol,
      preparedSelection: preparedExecutionSelection,
    })

    return {
      symbolChips: buildMarketSymbolChips(selectedSymbol),
      metricTiles: buildMarketMetricTiles({
        t,
        snapshot: tradingSnapshot,
      }),
      chartState: buildMarketChartStateModel({
        t,
        candlesCount: candles.length,
        candlesFetching: candlesQuery.isLoading || candlesQuery.isFetching,
        marketStatus,
      }),
      chartSeries: buildMarketChartSeriesModel(candles),
      strategyMatrix: buildStrategyDecisionMatrixModel({ t, signal: strategySignal }),
      portfolioPanel: buildStrategyPortfolioPanelModel({ t, signal: strategySignal, selectedSymbol }),
      strategyRegistry: buildStrategyRegistryPanelModel({ t, signal: strategySignal, selectedSymbol, orchestrationStatus }),
      executionRail,
      chartMarkers: buildMarketChartMarkersModel({ preparedSelection: preparedExecutionSelection }),
      orderbookPanel,
      spotlight: buildMarketSpotlightModel({
        t,
        snapshot: tradingSnapshot,
        executionRail,
        orderbookPanel,
      }),
    }
  }, [
    candles,
    candlesQuery.isFetching,
    candlesQuery.isLoading,
    marketStatus,
    orchestrationStatus,
    orderbook,
    preparedExecutionSelection,
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
    activeSymbol: selectedSymbol,
    summaryError,
    ...model,
    selectSymbol,
  }
}
