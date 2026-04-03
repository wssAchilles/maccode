import { useMemo } from 'react'
import { useShallow } from 'zustand/react/shallow'

import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import { useDormantSelector } from '../../store/useDormantSelector'
import { buildMatchingOrderBookPanelModel } from '../../view-models/orderbook'
import { buildPreparedExecutionSelection } from '../execution/read-models'
import {
  buildMarketExecutionRailModel,
  buildMarketSymbolChips,
} from '../market/view-models'

type Params = {
  active: boolean
}

export function useBookWorkspaceModel({ active }: Params) {
  const { t } = useI18n()
  const {
    selectedSymbol,
    orderEvents,
    orderbook,
    summaryError,
  } = useDormantSelector(
    active,
    useShallow((state) => ({
      selectedSymbol: state.marketStream.selected_symbol,
      orderEvents: state.executionTrading.order_events,
      orderbook: state.strategySummary.matching_orderbook,
      summaryError: state.strategySummary.last_error,
    })),
  )

  const setSelectedSymbol = useCerberusStore((state) => state.marketStreamActions.setSelectedSymbol)
  const syncExecutionFilters = useCerberusStore((state) => state.executionTradingActions.setFilters)

  const preparedSelection = useMemo(
    () => buildPreparedExecutionSelection(orderEvents, selectedSymbol),
    [orderEvents, selectedSymbol],
  )

  const model = useMemo(() => {
    const orderbookPanel = buildMatchingOrderBookPanelModel({ t, orderbook })
    const executionRail = buildMarketExecutionRailModel({
      t,
      selectedSymbol,
      preparedSelection,
    })

    return {
      symbolChips: buildMarketSymbolChips(selectedSymbol),
      orderbookPanel,
      executionRail,
      contextBand: {
        eyebrow: t('workspace.book.eyebrow'),
        title: selectedSymbol,
        hint: orderbookPanel.stale ? t('orderbook.staleHint') : executionRail.summary,
        accent: orderbookPanel.stale ? 'amber' as const : 'cyan' as const,
        items: [
          {
            id: 'best-bid',
            label: t('market.bestBid'),
            value: orderbookPanel.bestBidLabel,
            tone: 'positive' as const,
          },
          {
            id: 'best-ask',
            label: t('market.bestAsk'),
            value: orderbookPanel.bestAskLabel,
            tone: 'negative' as const,
          },
          {
            id: 'spread',
            label: t('orderbook.spread'),
            value: orderbookPanel.spreadLabel,
          },
          {
            id: 'liquidity-bias',
            label: t('orderbook.liquidityBias'),
            value: orderbookPanel.liquidityBiasLabel,
            tone: 'accent' as const,
          },
          {
            id: 'updated',
            label: t('orderbook.updated'),
            value: orderbookPanel.updatedAtLabel,
          },
        ],
      },
      spotlight: {
        summary: orderbookPanel.stale
          ? t('orderbook.stale')
          : `${selectedSymbol} ${t('orderbook.title')}`,
        hint: executionRail.summary,
        chips: [orderbookPanel.totalDepthLabel, orderbookPanel.depthBalanceLabel],
        accent: orderbookPanel.stale ? 'amber' as const : 'cyan' as const,
        postureLabel: t('workspace.book.title'),
        metrics: [
          {
            id: 'mid-price',
            label: t('orderbook.midPrice'),
            value: orderbookPanel.midPriceLabel,
            tone: 'accent' as const,
            visualPriority: 'primary' as const,
          },
          {
            id: 'total-depth',
            label: t('orderbook.totalDepth'),
            value: orderbookPanel.totalDepthLabel,
          },
          {
            id: 'depth-balance',
            label: t('orderbook.depthBalance'),
            value: orderbookPanel.depthBalanceLabel,
          },
          {
            id: 'liquidity-bias',
            label: t('orderbook.liquidityBias'),
            value: orderbookPanel.liquidityBiasLabel,
            tone: 'accent' as const,
          },
        ],
      },
      operatorSections: [
        {
          id: 'depth',
          title: t('workspace.market.operatorDepthTitle'),
          summary: t('workspace.market.operatorDepthDescription'),
          accent: orderbookPanel.stale ? 'amber' as const : 'cyan' as const,
          postureLabel: orderbookPanel.liquidityBiasLabel,
          visualPriority: 'hero' as const,
          items: orderbookPanel.band.items.slice(0, 4),
        },
        {
          id: 'pulse',
          title: t('workspace.market.executionRailTitle'),
          summary: t('workspace.market.executionRailDescription'),
          accent: 'amber' as const,
          items: executionRail.band?.items.slice(0, 4) ?? [],
        },
      ],
    }
  }, [orderbook, preparedSelection, selectedSymbol, t])

  const selectSymbol = (symbol: string) => {
    setSelectedSymbol(symbol)
    syncExecutionFilters({ symbol })
  }

  return {
    activeSymbol: selectedSymbol,
    selectSymbol,
    summaryError,
    ...model,
  }
}
