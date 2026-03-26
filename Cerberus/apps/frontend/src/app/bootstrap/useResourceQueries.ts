import { useQuery } from '@tanstack/react-query'

import { useCerberusStore } from '../../store'

export function useStrategySummaryResource(enabled: boolean) {
  const selectedSymbol = useCerberusStore((state) => state.marketStream.selected_symbol)

  return useQuery({
    queryKey: ['strategy-summary', selectedSymbol],
    enabled,
    staleTime: 4_000,
    refetchInterval: enabled ? 4_000 : false,
    refetchOnWindowFocus: false,
    queryFn: async () => {
      await useCerberusStore.getState().strategySummaryActions.refreshSummary()
      return useCerberusStore.getState().strategySummary
    },
  })
}

export function useCandlesResource(enabled: boolean) {
  const selectedSymbol = useCerberusStore((state) => state.marketStream.selected_symbol)

  return useQuery({
    queryKey: ['candles', selectedSymbol],
    enabled,
    staleTime: 30_000,
    refetchInterval: enabled ? 45_000 : false,
    refetchOnWindowFocus: false,
    queryFn: async () => {
      await useCerberusStore.getState().marketStreamActions.loadCandles()
      return useCerberusStore.getState().marketStream.candles
    },
  })
}

export function useTradingPolicyResource(enabled: boolean) {
  return useQuery({
    queryKey: ['trading-policy'],
    enabled,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
    queryFn: async () => {
      await useCerberusStore.getState().executionTradingActions.loadTradingPolicy()
      return useCerberusStore.getState().executionTrading.trading_policy
    },
  })
}

export function useBinanceRuleResource(enabled: boolean, symbol: string) {
  return useQuery({
    queryKey: ['binance-rule', symbol],
    enabled,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
    queryFn: async () => {
      await useCerberusStore.getState().executionTradingActions.loadBinanceRule(symbol)
      return useCerberusStore.getState().executionTrading.binance_rule
    },
  })
}

export function useRecentEventsResource(enabled: boolean) {
  const filterSymbol = useCerberusStore((state) => state.executionTrading.filter_symbol)
  const filterAccountId = useCerberusStore((state) => state.executionTrading.filter_account_id)
  const filterStatus = useCerberusStore((state) => state.executionTrading.filter_status)

  return useQuery({
    queryKey: ['recent-events', filterSymbol, filterAccountId, filterStatus],
    enabled,
    staleTime: 15_000,
    refetchOnWindowFocus: false,
    queryFn: async () => {
      await useCerberusStore.getState().executionTradingActions.loadRecentOrderEvents({
        symbol: filterSymbol,
        account_id: filterAccountId,
        status: filterStatus,
      })
      return useCerberusStore.getState().executionTrading.order_events
    },
  })
}
