import { describe, expect, it } from 'vitest'

import { runBinancePrecheck } from './precheck'

describe('runBinancePrecheck', () => {
  it('passes when quantity and price satisfy rule and policy', () => {
    const result = runBinancePrecheck({
      symbol: 'BTCUSDT',
      quantityText: '0.010',
      priceText: '60000',
      rule: {
        symbol: 'BTCUSDT',
        min_notional: 10,
        min_qty: 0.001,
        step_size: 0.001,
        tick_size: 0.1,
        refreshed_at: Date.now(),
      },
      policy: {
        enforced: true,
        binance_allowed_symbols: ['BTCUSDT'],
        alpaca_allowed_symbols: ['AAPL'],
        max_binance_order_qty: 1,
        max_binance_order_notional_usd: 100000,
      },
    })

    expect(result.ok).toBe(true)
    expect(result.checks.every((item) => item.status !== 'fail')).toBe(true)
  })

  it('fails when notional is below minimum', () => {
    const result = runBinancePrecheck({
      symbol: 'BTCUSDT',
      quantityText: '0.001',
      priceText: '200',
      rule: {
        symbol: 'BTCUSDT',
        min_notional: 20,
        min_qty: 0.001,
        step_size: 0.001,
        tick_size: 0.1,
        refreshed_at: Date.now(),
      },
      policy: {
        enforced: false,
        binance_allowed_symbols: [],
        alpaca_allowed_symbols: [],
      },
    })

    expect(result.ok).toBe(false)
    expect(result.checks.some((item) => item.id === 'min-notional' && item.status === 'fail')).toBe(true)
  })
})
