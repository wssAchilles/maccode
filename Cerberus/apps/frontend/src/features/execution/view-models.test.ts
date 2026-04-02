import { describe, expect, it } from 'vitest'

import { buildPreparedTradingSnapshot } from '../../view-models/workbench'
import { buildPreparedExecutionSelection } from './read-models'
import { buildExecutionHeroBandModel, buildExecutionInspectorBandModel } from './view-models'

const t = (key: string) => key

describe('execution view models', () => {
  it('builds an execution hero band from the prepared snapshot and execution selection', () => {
    const snapshot = buildPreparedTradingSnapshot({
      selectedSymbol: 'BTCUSDT',
      latest: {
        symbol: 'BTCUSDT',
        bid_price: '100.10',
        ask_price: '100.40',
        event_time: 1000,
      },
      latestBySymbol: {},
      strategySignal: {
        status: 'ready',
        signal: 'BUY',
        confidence: 0.72,
      },
      latestEvent: {
        id: 'evt-1',
        channel: 'trade.executions.default',
        payload: {},
        received_at: 1000,
        event_type: 'matching.order.submitted',
        symbol: 'BTCUSDT',
        status: 'accepted',
        lifecycle_phase: 'accepted',
        correlation_key: 'corr-1',
      },
    })
    const preparedSelection = buildPreparedExecutionSelection(
      [
        {
          id: 'evt-1',
          channel: 'trade.executions.default',
          payload: {},
          received_at: 1000,
          event_type: 'matching.order.submitted',
          symbol: 'BTCUSDT',
          status: 'accepted',
          lifecycle_phase: 'accepted',
          correlation_key: 'corr-1',
        },
      ],
      'BTCUSDT',
    )

    const band = buildExecutionHeroBandModel({
      t,
      snapshot,
      preparedSelection,
      tradingPolicy: {
        enforced: true,
        binance_allowed_symbols: ['BTCUSDT'],
        alpaca_allowed_symbols: [],
      },
      binanceRule: {
        symbol: 'BTCUSDT',
        min_qty: 0.001,
        step_size: 0.001,
        min_notional: 5,
        refreshed_at: 1000,
      },
    })

    expect(band.title).toBe('BTCUSDT')
    expect(band.items).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: 'signal', value: 'BUY' }),
        expect.objectContaining({ id: 'active-orders', value: '1' }),
        expect.objectContaining({ id: 'latest-lifecycle', value: 'accepted' }),
        expect.objectContaining({ id: 'guardrail-state', value: 'common.ready' }),
      ]),
    )
  })

  it('builds an execution inspector band for side replay', () => {
    const snapshot = buildPreparedTradingSnapshot({
      selectedSymbol: 'BTCUSDT',
      latest: {
        symbol: 'BTCUSDT',
        bid_price: '100.10',
        ask_price: '100.40',
        event_time: 1000,
      },
      latestBySymbol: {},
      strategySignal: {
        status: 'ready',
        signal: 'BUY',
        confidence: 0.72,
      },
      latestEvent: {
        id: 'evt-1',
        channel: 'trade.executions.default',
        payload: {},
        received_at: 1000,
        event_type: 'matching.order.submitted',
        symbol: 'BTCUSDT',
        status: 'accepted',
        lifecycle_phase: 'accepted',
        correlation_key: 'corr-1',
      },
    })
    const preparedSelection = buildPreparedExecutionSelection(
      [
        {
          id: 'evt-1',
          channel: 'trade.executions.default',
          payload: {},
          received_at: 1000,
          event_type: 'matching.order.submitted',
          symbol: 'BTCUSDT',
          status: 'accepted',
          lifecycle_phase: 'accepted',
          correlation_key: 'corr-1',
        },
      ],
      'BTCUSDT',
    )

    const band = buildExecutionInspectorBandModel({
      t,
      snapshot,
      preparedSelection,
      orderbookPanel: {
        totalDepthLabel: '2.000',
        updatedAtLabel: '1/1/1970, 12:10:00 AM',
        liquidityBiasLabel: 'balanced',
      },
    })

    expect(band.title).toBe('BTCUSDT')
    expect(band.items).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: 'signal', value: 'BUY' }),
        expect.objectContaining({ id: 'active-orders', value: '1' }),
        expect.objectContaining({ id: 'total-depth', value: '2.000' }),
      ]),
    )
  })
})
