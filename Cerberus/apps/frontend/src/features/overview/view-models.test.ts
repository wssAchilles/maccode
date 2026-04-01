import { describe, expect, it } from 'vitest'

import {
  buildOverviewMetricTiles,
  buildOverviewPersistenceItems,
  buildOverviewRecentSignalCards,
  buildOverviewSpotlightModel,
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

  it('builds an overview spotlight from snapshot and domain counts', () => {
    const snapshot = buildPreparedTradingSnapshot({
      selectedSymbol: 'BTCUSDT',
      latest: {
        symbol: 'BTCUSDT',
        bid_price: '100.0',
        ask_price: '100.4',
        event_time: 1_000,
      },
      latestBySymbol: {},
      strategySignal: {
        status: 'ready',
        signal: 'HOLD',
        confidence: 0.42,
      },
      latestEvent: {
        id: 'evt-2',
        channel: 'trade.executions.default',
        payload: {},
        received_at: 1_000,
        event_type: 'strategy.signal.generated',
        symbol: 'BTCUSDT',
        status: 'HOLD',
        lifecycle_phase: 'submit',
        correlation_key: 'corr-2',
      },
    })

    const spotlight = buildOverviewSpotlightModel({
      t,
      snapshot,
      readyCount: 2,
      attentionCount: 1,
    })

    expect(spotlight.summary).toContain('BTCUSDT')
    expect(spotlight.metrics).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: 'mid-price', value: '100.200000' }),
        expect.objectContaining({ id: 'services-ready', value: '2' }),
        expect.objectContaining({ id: 'services-attention', value: '1' }),
      ]),
    )
  })

  it('prepares recent signal cards for replay in overview', () => {
    const cards = buildOverviewRecentSignalCards({
      t,
      recentSignals: [
        {
          strategy_id: 'mom-1',
          symbol: 'BTCUSDT',
          signal: 'BUY',
          confidence: 0.77,
          created_at: '2026-03-27T10:00:00Z',
        },
      ],
    })

    expect(cards).toHaveLength(1)
    expect(cards[0]).toMatchObject({
      signal: 'BUY',
      symbol: 'BTCUSDT',
      items: expect.arrayContaining([
        { id: 'confidence', label: 'strategy.confidence', value: '0.770000' },
        { id: 'strategy', label: 'workspace.strategy.auditStrategy', value: 'mom-1' },
      ]),
    })
    expect(cards[0].items[2]?.label).toBe('common.updatedAt')
    expect(cards[0].items[2]?.value).not.toBe('—')
  })
})
