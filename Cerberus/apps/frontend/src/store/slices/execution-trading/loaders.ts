import { requestEnvelope } from '../../../lib/http'
import type { BinanceRule, OrderEvent, TradingPolicy } from '../../../types/contracts'

export type RecentOrderFilters = {
  symbol?: string
  account_id?: string
  order_id?: string
  status?: string
  request_id?: string
}

function appendFilter(params: URLSearchParams, key: keyof RecentOrderFilters, value?: string) {
  const normalized = value?.trim()
  if (!normalized || normalized === 'ALL') {
    return
  }
  params.set(key, normalized)
}

export async function loadRecentOrderEventsEnvelope(
  gatewayBase: string,
  filters?: RecentOrderFilters,
) {
  const params = new URLSearchParams()
  params.set('limit', '200')
  appendFilter(params, 'symbol', filters?.symbol)
  appendFilter(params, 'account_id', filters?.account_id)
  appendFilter(params, 'order_id', filters?.order_id)
  appendFilter(params, 'status', filters?.status)
  appendFilter(params, 'request_id', filters?.request_id)

  return requestEnvelope<{ count: number; events: OrderEvent[]; request_id?: string }>(
    `${gatewayBase}/api/v1/orders/events/recent?${params.toString()}`,
  )
}

export async function loadTradingPolicyEnvelope(gatewayBase: string) {
  return requestEnvelope<{ policy?: TradingPolicy }>(`${gatewayBase}/api/v1/trading/policy`)
}

export async function loadBinanceRuleEnvelope(gatewayBase: string, symbol: string) {
  return requestEnvelope<{ rule?: BinanceRule }>(
    `${gatewayBase}/api/v1/binance/symbol-rules?symbol=${encodeURIComponent(symbol)}`,
  )
}
