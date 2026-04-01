import { describe, expect, it, vi } from 'vitest'

import type { MatchingOrderBook } from '../types/contracts'
import { buildMatchingOrderBookPanelModel } from './orderbook'

const t = (key: string) => key

describe('orderbook view models', () => {
  it('builds a localized orderbook panel model from a snapshot', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-01T08:00:05.000Z'))

    const orderbook: MatchingOrderBook = {
      enabled: true,
      degraded: false,
      symbol: 'BTCUSDT',
      depth: 10,
      generated_at_ms: Date.parse('2026-04-01T08:00:00.000Z'),
      bids: [
        { price: 100.123456, total_quantity: 3.5, order_count: 2 },
      ],
      asks: [
        { price: 100.223456, total_quantity: 4.25, order_count: 3 },
      ],
    }

    const model = buildMatchingOrderBookPanelModel({ t, orderbook })

    expect(model).toMatchObject({
      title: 'orderbook.title',
      description: 'BTCUSDT · depth 10',
      bestBidTitle: 'market.bestBid',
      bestBidLabel: '100.123456',
      bestAskLabel: '100.223456',
      spreadLabel: '0.100000',
      depthBalanceLabel: '3.500 / 4.250',
      stale: false,
    })
    expect(model.bids[0]).toMatchObject({
      priceLabel: '100.123456',
      quantityLabel: '3.500000',
      orderCountLabel: '2',
    })

    vi.useRealTimers()
  })

  it('returns degraded empty copy when orderbook is unavailable', () => {
    const model = buildMatchingOrderBookPanelModel({
      t,
      orderbook: {
        enabled: true,
        degraded: true,
        symbol: 'ETHUSDT',
        depth: 10,
        bids: [],
        asks: [],
        generated_at_ms: Date.parse('2026-04-01T08:00:00.000Z'),
        reason: 'matching backend timeout',
      },
    })

    expect(model.emptyTitle).toBe('orderbook.emptyDegradedTitle')
    expect(model.emptyBody).toBe('matching backend timeout')
  })

  it('reuses prepared level rows and computes stale from explicit freshness input', () => {
    const orderbook: MatchingOrderBook = {
      enabled: true,
      degraded: false,
      symbol: 'BTCUSDT',
      depth: 5,
      generated_at_ms: 1_000,
      bids: [{ price: 100.1, total_quantity: 2.25, order_count: 1 }],
      asks: [{ price: 100.2, total_quantity: 3.5, order_count: 2 }],
    }

    const first = buildMatchingOrderBookPanelModel({ t, orderbook, nowMs: 5_000 })
    const second = buildMatchingOrderBookPanelModel({ t, orderbook, nowMs: 12_000 })

    expect(first.bids).toBe(second.bids)
    expect(first.asks).toBe(second.asks)
    expect(first.stale).toBe(false)
    expect(second.stale).toBe(true)
  })
})
