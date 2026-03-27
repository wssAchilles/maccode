import { describe, expect, it } from 'vitest'

import { buildMarketMetricTiles, buildMarketSymbolChips } from './view-models'

const t = (key: string) => key

describe('market view models', () => {
  it('builds symbol chips with one active symbol', () => {
    expect(buildMarketSymbolChips('ETHUSDT')).toEqual([
      { id: 'BTCUSDT', label: 'BTCUSDT', active: false },
      { id: 'ETHUSDT', label: 'ETHUSDT', active: true },
    ])
  })

  it('builds market metric tiles from current quote and signal', () => {
    const tiles = buildMarketMetricTiles({
      t,
      displayQuote: {
        symbol: 'BTCUSDT',
        bid_price: '100.12',
        ask_price: '100.56',
        event_time: 1000,
      },
      strategySignal: {
        status: 'ready',
        signal: 'BUY',
        confidence: 0.83,
        symbol: 'BTCUSDT',
      },
      latestEvent: {
        id: 'evt-1',
        channel: 'trade.executions.default',
        payload: {},
        received_at: 1000,
        event_type: 'execution.created',
        symbol: 'BTCUSDT',
        status: 'FILLED',
      },
    })

    expect(tiles[0]).toMatchObject({ id: 'best-bid', value: '100.12' })
    expect(tiles[1]).toMatchObject({ id: 'best-ask', value: '100.56' })
    expect(tiles[2]).toMatchObject({
      id: 'signal',
      value: 'BUY',
      hint: 'strategy.confidence: 0.830000',
    })
    expect(tiles[3]).toMatchObject({
      id: 'execution-stream',
      value: 'execution.created · BTCUSDT · FILLED',
    })
  })
})
