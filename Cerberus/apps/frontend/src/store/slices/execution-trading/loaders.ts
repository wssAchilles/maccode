import { requestEnvelope } from '../../../lib/http'
import type { BinanceRule, OrderEvent, TradingPolicy } from '../../../types/contracts'

export async function loadRecentOrderEventsEnvelope(gatewayBase: string) {
  return requestEnvelope<{ count: number; events: OrderEvent[] }>(
    `${gatewayBase}/api/v1/orders/events/recent?limit=200`,
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
