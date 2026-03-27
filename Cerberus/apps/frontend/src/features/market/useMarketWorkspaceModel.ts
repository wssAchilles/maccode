import { useMemo } from 'react'

import { useCandlesResource } from '../../app/bootstrap/useResourceQueries'
import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import { buildMarketMetricTiles, buildMarketSymbolChips } from './view-models'

type Params = {
  active: boolean
}

export function useMarketWorkspaceModel({ active }: Params) {
  const { t } = useI18n()
  const selectedSymbol = useCerberusStore((state) => state.marketStream.selected_symbol)
  const latest = useCerberusStore((state) => state.marketStream.latest)
  const latestBySymbol = useCerberusStore((state) => state.marketStream.latest_by_symbol)
  const latestEvent = useCerberusStore((state) => state.executionTrading.latest_event)
  const candles = useCerberusStore((state) => state.marketStream.candles)
  const summaryError = useCerberusStore((state) => state.strategySummary.last_error)
  const strategySignal = useCerberusStore((state) => state.strategySummary.signal)
  const orderbook = useCerberusStore((state) => state.strategySummary.matching_orderbook)
  const setSelectedSymbol = useCerberusStore((state) => state.marketStreamActions.setSelectedSymbol)

  useCandlesResource(active)

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

  return {
    activeSymbol: selectedSymbol,
    candles,
    summaryError,
    orderbook,
    symbolChips,
    metricTiles,
    selectSymbol: setSelectedSymbol,
  }
}
