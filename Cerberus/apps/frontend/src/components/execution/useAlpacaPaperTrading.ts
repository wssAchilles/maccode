import { useEffect, useMemo, useState } from 'react'

import { formatAppError, toAppError } from '../../lib/http'
import type { TradingPolicy } from '../../types/contracts'
import { callGateway } from './gateway'
import { type GatewayResponse, parsePositiveNumber, readGatewayRequestId } from './types'

type FlowEvent = {
  step: 'submit' | 'cancel'
  state: 'active' | 'success' | 'error'
  reason?: string
  requestId?: string
}

type Params = {
  active: boolean
  gatewayBase: string
  tradingPolicy: TradingPolicy | null
  onFlowEvent?: (event: FlowEvent) => void
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
  active,
  gatewayBase,
  tradingPolicy,
  onFlowEvent,
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
    if (!active) {
      return
    }
    const loadAccount = async () => {
      const accountPayload = await callGateway('/api/v1/alpaca/account', gatewayBase, { method: 'GET' })
      setAccount(accountPayload)
    }
    void loadAccount()
  }, [active, gatewayBase])

  const canCancel = useMemo(() => Boolean(readLastOrderId(result)), [result])

  const submit = async () => {
    const qty = parsePositiveNumber(quantity)
    if (qty === null) {
      onFlowEvent?.({
        step: 'submit',
        state: 'error',
        reason: 'qty must be a positive number',
      })
      setResult({
        status: 400,
        at: new Date().toISOString(),
        body: { error: 'qty must be a positive number' },
        error: {
          code: 'validation_error',
          message: 'qty must be a positive number',
        },
      })
      return
    }

    if (
      orderType === 'limit' &&
      tradingPolicy?.max_alpaca_limit_notional_usd &&
      parsePositiveNumber(limitPrice) !== null &&
      qty * Number(limitPrice) > tradingPolicy.max_alpaca_limit_notional_usd
    ) {
      onFlowEvent?.({
        step: 'submit',
        state: 'error',
        reason: `notional above policy max ${tradingPolicy.max_alpaca_limit_notional_usd}`,
      })
      setResult({
        status: 400,
        at: new Date().toISOString(),
        body: { error: `notional above policy max ${tradingPolicy.max_alpaca_limit_notional_usd}` },
        error: {
          code: 'policy_rejected',
          message: `notional above policy max ${tradingPolicy.max_alpaca_limit_notional_usd}`,
        },
      })
      return
    }

    setSubmitting(true)
    onFlowEvent?.({
      step: 'submit',
      state: 'active',
      reason: 'submitting order to gateway',
    })
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
      if (payload.status < 400) {
        onFlowEvent?.({
          step: 'submit',
          state: 'success',
          reason: 'order submit accepted',
          requestId: readGatewayRequestId(payload.body),
        })
      } else {
        const error = toAppError(payload.error ?? payload.body, 'submit_failed')
        onFlowEvent?.({
          step: 'submit',
          state: 'error',
          reason: formatAppError(error),
          requestId: error.request_id,
        })
      }
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
    onFlowEvent?.({
      step: 'cancel',
      state: 'active',
      reason: 'canceling order via gateway',
    })
    try {
      const payload = await callGateway(
        `/api/v1/alpaca/orders/${encodeURIComponent(orderId)}/cancel`,
        gatewayBase,
        { method: 'POST' },
      )
      setResult(payload)
      if (payload.status < 400) {
        onFlowEvent?.({
          step: 'cancel',
          state: 'success',
          reason: 'cancel accepted',
          requestId: readGatewayRequestId(payload.body),
        })
      } else {
        const error = toAppError(payload.error ?? payload.body, 'cancel_failed')
        onFlowEvent?.({
          step: 'cancel',
          state: 'error',
          reason: formatAppError(error),
          requestId: error.request_id,
        })
      }
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
