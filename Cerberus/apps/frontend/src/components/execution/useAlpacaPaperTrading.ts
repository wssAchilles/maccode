import { useEffect, useMemo, useState } from 'react'

import type { TradingPolicy } from '../../types/contracts'
import { callGateway } from './gateway'
import { type GatewayResponse, parsePositiveNumber } from './types'

type Params = {
  gatewayBase: string
  tradingPolicy: TradingPolicy | null
}

export type AlpacaPaperTradingModel = {
  symbol: string
  quantity: string
  side: 'buy' | 'sell'
  orderType: 'market' | 'limit'
  timeInForce: 'day' | 'gtc' | 'ioc' | 'opg' | 'cls'
  limitPrice: string
  submitting: boolean
  canceling: boolean
  canCancel: boolean
  result: GatewayResponse | null
  account: GatewayResponse | null
  setSymbol: (value: string) => void
  setQuantity: (value: string) => void
  setSide: (value: 'buy' | 'sell') => void
  setOrderType: (value: 'market' | 'limit') => void
  setTimeInForce: (value: 'day' | 'gtc' | 'ioc' | 'opg' | 'cls') => void
  setLimitPrice: (value: string) => void
  submit: () => Promise<void>
  cancel: () => Promise<void>
}

function readLastOrderId(result: GatewayResponse | null): string | null {
  const body = result?.body
  if (!body || typeof body !== 'object') {
    return null
  }
  const id = (body as Record<string, unknown>).id
  return typeof id === 'string' && id.length > 0 ? id : null
}

export function useAlpacaPaperTrading({
  gatewayBase,
  tradingPolicy,
}: Params): AlpacaPaperTradingModel {
  const [symbol, setSymbol] = useState('AAPL')
  const [quantity, setQuantity] = useState('1')
  const [side, setSide] = useState<'buy' | 'sell'>('buy')
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market')
  const [timeInForce, setTimeInForce] = useState<'day' | 'gtc' | 'ioc' | 'opg' | 'cls'>('day')
  const [limitPrice, setLimitPrice] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [canceling, setCanceling] = useState(false)
  const [result, setResult] = useState<GatewayResponse | null>(null)
  const [account, setAccount] = useState<GatewayResponse | null>(null)

  useEffect(() => {
    const loadAccount = async () => {
      const accountPayload = await callGateway('/api/v1/alpaca/account', gatewayBase, { method: 'GET' })
      setAccount(accountPayload)
    }
    void loadAccount()
  }, [gatewayBase])

  const canCancel = useMemo(() => Boolean(readLastOrderId(result)), [result])

  const submit = async () => {
    const qty = parsePositiveNumber(quantity)
    if (qty === null) {
      setResult({
        status: 400,
        at: new Date().toISOString(),
        body: { error: 'qty must be a positive number' },
      })
      return
    }

    if (
      orderType === 'limit' &&
      tradingPolicy?.max_alpaca_limit_notional_usd &&
      parsePositiveNumber(limitPrice) !== null &&
      qty * Number(limitPrice) > tradingPolicy.max_alpaca_limit_notional_usd
    ) {
      setResult({
        status: 400,
        at: new Date().toISOString(),
        body: { error: `notional above policy max ${tradingPolicy.max_alpaca_limit_notional_usd}` },
      })
      return
    }

    setSubmitting(true)
    try {
      const payload = await callGateway('/api/v1/alpaca/orders', gatewayBase, {
        method: 'POST',
        body: JSON.stringify({
          symbol: symbol.toUpperCase(),
          qty: quantity,
          side,
          type: orderType,
          time_in_force: timeInForce,
          limit_price: orderType === 'limit' ? limitPrice : undefined,
        }),
      })
      setResult(payload)
    } finally {
      setSubmitting(false)
    }
  }

  const cancel = async () => {
    const orderId = readLastOrderId(result)
    if (!orderId) {
      return
    }
    setCanceling(true)
    try {
      const payload = await callGateway(
        `/api/v1/alpaca/orders/${encodeURIComponent(orderId)}/cancel`,
        gatewayBase,
        { method: 'POST' },
      )
      setResult(payload)
    } finally {
      setCanceling(false)
    }
  }

  return {
    symbol,
    quantity,
    side,
    orderType,
    timeInForce,
    limitPrice,
    submitting,
    canceling,
    canCancel,
    result,
    account,
    setSymbol,
    setQuantity,
    setSide,
    setOrderType,
    setTimeInForce,
    setLimitPrice,
    submit,
    cancel,
  }
}
