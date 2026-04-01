import { useEffect, useMemo, useRef, useState } from 'react'

import { useCerberusStore } from '../../store'

type ResourceStatus = {
  isLoading: boolean
  isFetching: boolean
}

function useStoreRefresh({
  enabled,
  intervalMs,
  refresh,
  refreshKey,
}: {
  enabled: boolean
  intervalMs?: number
  refresh: () => Promise<void>
  refreshKey?: string
}): ResourceStatus {
  const [isFetching, setIsFetching] = useState(false)
  const refreshRef = useRef(refresh)
  refreshRef.current = refresh

  useEffect(() => {
    if (!enabled) {
      setIsFetching(false)
      return
    }

    let disposed = false

    const runRefresh = async () => {
      setIsFetching(true)
      try {
        await refreshRef.current()
      } finally {
        if (!disposed) {
          setIsFetching(false)
        }
      }
    }

    void runRefresh()

    if (!intervalMs) {
      return () => {
        disposed = true
      }
    }

    const handle = window.setInterval(() => {
      void runRefresh()
    }, intervalMs)

    return () => {
      disposed = true
      window.clearInterval(handle)
    }
  }, [enabled, intervalMs, refreshKey])

  return useMemo(
    () => ({
      isLoading: enabled && isFetching,
      isFetching,
    }),
    [enabled, isFetching],
  )
}

export function useStrategySummaryResource(enabled: boolean): void {
  const selectedSymbol = useCerberusStore((state) => state.marketStream.selected_symbol)

  useStoreRefresh({
    enabled,
    intervalMs: 4_000,
    refreshKey: selectedSymbol,
    refresh: async () => {
      await useCerberusStore.getState().strategySummaryActions.refreshSummary()
    },
  })
}

export function useCandlesResource(enabled: boolean) {
  const selectedSymbol = useCerberusStore((state) => state.marketStream.selected_symbol)

  const status = useStoreRefresh({
    enabled,
    intervalMs: 45_000,
    refreshKey: selectedSymbol,
    refresh: async () => {
      await useCerberusStore.getState().marketStreamActions.loadCandles()
    },
  })

  return status
}

export function useTradingPolicyResource(enabled: boolean): void {
  useStoreRefresh({
    enabled,
    intervalMs: 60_000,
    refresh: async () => {
      await useCerberusStore.getState().executionTradingActions.loadTradingPolicy()
    },
  })
}

export function useBinanceRuleResource(enabled: boolean, symbol: string): void {
  useStoreRefresh({
    enabled,
    intervalMs: 60_000,
    refreshKey: symbol,
    refresh: async () => {
      await useCerberusStore.getState().executionTradingActions.loadBinanceRule(symbol)
    },
  })
}

export function useRecentEventsResource(enabled: boolean): void {
  const filterSymbol = useCerberusStore((state) => state.executionTrading.filter_symbol)
  const filterAccountId = useCerberusStore((state) => state.executionTrading.filter_account_id)
  const filterStatus = useCerberusStore((state) => state.executionTrading.filter_status)

  useStoreRefresh({
    enabled,
    intervalMs: 15_000,
    refreshKey: `${filterSymbol}:${filterAccountId}:${filterStatus}`,
    refresh: async () => {
      await useCerberusStore.getState().executionTradingActions.loadRecentOrderEvents({
        symbol: filterSymbol,
        account_id: filterAccountId,
        status: filterStatus,
      })
    },
  })
}
