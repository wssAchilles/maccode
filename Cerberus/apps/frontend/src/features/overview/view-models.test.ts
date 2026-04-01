import { describe, expect, it } from 'vitest'

import {
  buildOverviewMetricTiles,
  buildOverviewPersistenceItems,
} from './view-models'
import { buildPreparedTradingSnapshot } from '../../view-models/workbench'

const t = (key: string) => key

describe('overview view models', () => {
  it('builds overview metric tiles from workspace state', () => {
    const snapshot = buildPreparedTradingSnapshot({
      selectedSymbol: 'BTCUSDT',
      latest: {
        symbol: 'BTCUSDT',
        bid_price: '99.1',
        ask_price: '99.4',
        event_time: 1000,
      },
      latestBySymbol: {},
      strategySignal: {
        status: 'ready',
        signal: 'SELL',
        confidence: 0.61,
        symbol: 'BTCUSDT',
      },
      latestEvent: {
        id: 'evt-1',
        channel: 'trade.executions.default',
        payload: {},
        received_at: 1000,
        event_time: '2026-03-27T10:00:00Z',
        event_type: 'execution.updated',
        symbol: 'BTCUSDT',
        status: 'PARTIALLY_FILLED',
      },
      heartbeat: 'hb',
    })

    const tiles = buildOverviewMetricTiles({
      t,
      snapshot,
    })

    expect(tiles[0]).toMatchObject({ id: 'best-bid', value: '99.1', hint: 'BTCUSDT' })
    expect(tiles[1]).toMatchObject({ id: 'best-ask', value: '99.4', hint: 'BTCUSDT' })
    expect(tiles[2]).toMatchObject({
      id: 'signal',
      value: 'SELL',
      hint: 'strategy.confidence: 0.610000',
    })
    expect(tiles[3]).toMatchObject({
      id: 'feedback',
      value: 'execution.updated · BTCUSDT · PARTIALLY_FILLED',
    })
  })

  it('builds persistence digest items', () => {
    const items = buildOverviewPersistenceItems({
      t,
      persistenceStatus: {
        status: 'ok',
        worker: {
          processed_ticks: 44,
          has_last_signal: true,
        },
        stores: {
          supabase_enabled: true,
          firebase_enabled: true,
          supabase_table: 'strategy_signals',
          firebase_collection: 'signals',
        },
      },
    })

    expect(items).toEqual([
      { id: 'worker', label: 'strategy.ticksProcessed', value: '44' },
      { id: 'supabase', label: 'Supabase', value: 'true' },
      { id: 'firebase', label: 'Firestore', value: 'true' },
    ])
  })
})
