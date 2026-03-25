import { useEffect, useMemo, useState } from 'react'

import { runBinancePrecheck, type PrecheckResult } from '../../domain/trading/precheck'
import { formatAppError, toAppError } from '../../lib/http'
import type { BinanceRule, TradingPolicy } from '../../types/contracts'
import { callGateway } from './gateway'
import { type GatewayResponse, type Stage, parsePositiveNumber, readGatewayRequestId } from './types'

type FlowEvent = {
  step: 'precheck' | 'submit'
  state: 'active' | 'success' | 'error'
  reason?: string
  requestId?: string
}

type Params = {
  selectedSymbol: string
  latestBid?: string
  latestAsk?: string
  gatewayBase: string
  rule: BinanceRule | null
  policy: TradingPolicy | null
  onFlowEvent?: (event: FlowEvent) => void
}

export type BinanceOrderTestModel = {
  side: 'BUY' | 'SELL'
  quantity: string
  price: string
  priceHint: string
  submitting: boolean
  result: GatewayResponse | null
  precheck: PrecheckResult | null
  stage: Stage
  notional: number | null
  setSide: (side: 'BUY' | 'SELL') => void
  setQuantity: (quantity: string) => void
  setPrice: (price: string) => void
  runPrecheck: () => void
  submit: () => Promise<void>
}

export function useBinanceOrderTest({
  selectedSymbol,
  latestBid,
  latestAsk,
  gatewayBase,
  rule,
  policy,
  onFlowEvent,
}: Params): BinanceOrderTestModel {
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY')
  const [quantity, setQuantity] = useState('0.002')
  const [price, setPrice] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<GatewayResponse | null>(null)
  const [precheck, setPrecheck] = useState<PrecheckResult | null>(null)
  const [stage, setStage] = useState<Stage>('idle')

  const priceHint = useMemo(() => {
    if (side === 'BUY') {
      return latestAsk ?? ''
    }
    return latestBid ?? ''
  }, [latestAsk, latestBid, side])

  useEffect(() => {
    if (!price && priceHint) {
      setPrice(priceHint)
    }
  }, [price, priceHint])

  const notional = useMemo(() => {
    const qty = parsePositiveNumber(quantity)
    const parsedPrice = parsePositiveNumber(price)
    if (qty === null || parsedPrice === null) {
      return null
    }
    return qty * parsedPrice
  }, [price, quantity])

  const runPrecheck = () => {
    const checked = runBinancePrecheck({
      symbol: selectedSymbol,
      quantityText: quantity,
      priceText: price,
      rule,
      policy,
    })
    setPrecheck(checked)
    setStage(checked.ok ? 'prechecked' : 'rejected')
    onFlowEvent?.({
      step: 'precheck',
      state: checked.ok ? 'success' : 'error',
      reason: checked.checks.find((item) => item.status === 'fail')?.message ?? 'precheck evaluated',
    })
  }

  const submit = async () => {
    const checked = runBinancePrecheck({
      symbol: selectedSymbol,
      quantityText: quantity,
      priceText: price,
      rule,
      policy,
    })
    setPrecheck(checked)

    if (!checked.ok) {
      setStage('rejected')
      onFlowEvent?.({
        step: 'submit',
        state: 'error',
        reason: checked.checks.find((item) => item.status === 'fail')?.message ?? 'precheck blocked submit',
      })
      return
    }

    setSubmitting(true)
    setStage('submitting')
    onFlowEvent?.({
      step: 'submit',
      state: 'active',
      reason: 'submitting order to gateway',
    })
    try {
      const payload = await callGateway('/api/v1/binance/order/test', gatewayBase, {
        method: 'POST',
        body: JSON.stringify({
          symbol: selectedSymbol,
          side,
          order_type: 'LIMIT',
          quantity,
          price,
          time_in_force: 'GTC',
        }),
      })
      setResult(payload)
      setStage(payload.status < 400 ? 'submitted' : 'rejected')
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

  return {
    side,
    quantity,
    price,
    priceHint,
    submitting,
    result,
    precheck,
    stage,
    notional,
    setSide,
    setQuantity,
    setPrice,
    runPrecheck,
    submit,
  }
}
