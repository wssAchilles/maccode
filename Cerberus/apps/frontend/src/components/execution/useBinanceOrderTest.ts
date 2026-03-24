import { useEffect, useMemo, useState } from 'react'

import { runBinancePrecheck, type PrecheckResult } from '../../domain/trading/precheck'
import type { BinanceRule, TradingPolicy } from '../../types/contracts'
import { callGateway } from './gateway'
import { type GatewayResponse, type Stage, parsePositiveNumber } from './types'

type Params = {
  selectedSymbol: string
  latestBid?: string
  latestAsk?: string
  gatewayBase: string
  rule: BinanceRule | null
  policy: TradingPolicy | null
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
      return
    }

    setSubmitting(true)
    setStage('submitting')
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
