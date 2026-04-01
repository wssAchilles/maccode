import { describe, expect, it } from 'vitest'

import type { Candle } from '../../types/contracts'
import { buildPreparedExecutionSelection } from '../execution/read-models'
import {
  buildMarketChartMarkersModel,
  buildMarketChartSeriesModel,
  buildMarketChartStateModel,
  buildMarketExecutionRailModel,
  buildMarketMetricTiles,
  buildMarketSymbolChips,
  getMarketChartReplayStartIndex,
  isSameMarketChartCandle,
} from './view-models'
import { buildPreparedTradingSnapshot } from '../../view-models/workbench'

const t = (key: string) => key

describe('market view models', () => {
  it('builds symbol chips with one active symbol', () => {
    expect(buildMarketSymbolChips('ETHUSDT')).toEqual([
      { id: 'BTCUSDT', label: 'BTCUSDT', active: false },
      { id: 'ETHUSDT', label: 'ETHUSDT', active: true },
    ])
  })

  it('builds market metric tiles from current quote and signal', () => {
    const snapshot = buildPreparedTradingSnapshot({
      selectedSymbol: 'BTCUSDT',
      latest: {
        symbol: 'BTCUSDT',
        bid_price: '100.12',
        ask_price: '100.56',
        event_time: 1000,
      },
      latestBySymbol: {},
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

    const tiles = buildMarketMetricTiles({
      t,
      snapshot,
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

  it('returns a loading chart state before the first candle batch arrives', () => {
    const state = buildMarketChartStateModel({
      t,
      candlesCount: 0,
      candlesFetching: true,
      marketStatus: {
        state: 'ready',
        last_update_ms: null,
        stale: false,
      },
    })

    expect(state).toMatchObject({
      state: 'loading',
      title: 'market.chartLoadingTitle',
      hint: 'market.chartLoadingHint',
    })
  })

  it('returns an error chart state when candle loading fails', () => {
    const state = buildMarketChartStateModel({
      t,
      candlesCount: 0,
      candlesFetching: false,
      marketStatus: {
        state: 'error',
        last_update_ms: null,
        stale: true,
        reason: 'market_candles_failed',
      },
    })

    expect(state).toMatchObject({
      state: 'error',
      title: 'market.chartErrorTitle',
      hint: 'market_candles_failed',
    })
  })

  it('prepares normalized candle points once per candle batch', () => {
    const candles: Candle[] = [
      [1712000000000, '100.1', '101.2', '99.8', '100.9', '12.5'],
      [1712000060000, '100.9', '102.0', '100.5', '101.7', '18.4'],
    ]

    const first = buildMarketChartSeriesModel(candles)
    const second = buildMarketChartSeriesModel(candles)

    expect(first).toBe(second)
    expect(first.points).toEqual([
      { time: 1712000000, open: 100.1, high: 101.2, low: 99.8, close: 100.9 },
      { time: 1712000060, open: 100.9, high: 102, low: 100.5, close: 101.7 },
    ])
    expect(first.firstTime).toBe(1712000000)
    expect(first.lastTime).toBe(1712000060)
    expect(Array.from(first.prefixHashes)).toHaveLength(2)
    expect(first.prefixHashes[1]).not.toBe(first.prefixHashes[0])
  })

  it('prepares chart markers from execution events', () => {
    const preparedSelection = buildPreparedExecutionSelection(
      [
        {
          id: 'fill-1',
          channel: 'trade.executions.default',
          payload: {},
          received_at: 1712000000000,
          event_time: '2024-04-02T12:00:00.000Z',
          event_type: 'execution.fill',
          symbol: 'BTCUSDT',
          status: 'FILLED',
          execution_id: 'exec-1',
          lifecycle_phase: 'fill',
          correlation_key: 'corr-1',
        },
      ],
      'BTCUSDT',
    )
    const markers = buildMarketChartMarkersModel({
      preparedSelection,
    })

    expect(markers).toEqual([
      {
        id: 'fill-1',
        time: 1712059200,
        position: 'belowBar',
        shape: 'arrowUp',
        color: '#15803d',
        text: 'exec-1',
      },
    ])
  })

  it('builds a replay plan for trailing candle updates', () => {
    const previous = buildMarketChartSeriesModel([
      [1712000000000, '100', '101', '99', '100.5', '12'],
      [1712000060000, '100.5', '102', '100', '101.7', '18'],
    ])
    const next = buildMarketChartSeriesModel([
      [1712000000000, '100', '101', '99', '100.5', '12'],
      [1712000060000, '100.5', '102', '100', '102.1', '18'],
      [1712000120000, '102.1', '103', '101.8', '102.8', '15'],
    ])

    expect(getMarketChartReplayStartIndex(previous, next)).toBe(1)
  })

  it('forces a chart reset when historical candles change', () => {
    const previous = buildMarketChartSeriesModel([
      [1712000000000, '100', '101', '99', '100.5', '12'],
      [1712000060000, '100.5', '102', '100', '101.7', '18'],
    ])
    const next = buildMarketChartSeriesModel([
      [1712000000000, '100', '104', '99', '100.5', '12'],
      [1712000060000, '100.5', '102', '100', '101.7', '18'],
    ])

    expect(getMarketChartReplayStartIndex(previous, next)).toBe(-1)
  })

  it('compares chart candles by normalized point values', () => {
    const series = buildMarketChartSeriesModel([
      [1712000000000, '100', '101', '99', '100.5', '12'],
      [1712000060000, '100.5', '102', '100', '101.7', '18'],
    ])

    expect(isSameMarketChartCandle(series.points[0], series.points[0])).toBe(true)
    expect(isSameMarketChartCandle(series.points[0], series.points[1])).toBe(false)
  })

  it('marks the execution rail stale with shared freshness semantics', () => {
    const preparedSelection = buildPreparedExecutionSelection(
      [
        {
          id: 'evt-1',
          channel: 'trade.executions.default',
          payload: {},
          received_at: 1000,
          event_time: '1970-01-01T00:10:00.000Z',
          event_type: 'execution.fill',
          symbol: 'BTCUSDT',
          status: 'FILLED',
          lifecycle_phase: 'fill',
          correlation_key: 'corr-1',
          request_id: 'req-1',
          execution_id: 'exec-1',
        },
      ],
      'BTCUSDT',
    )
    const model = buildMarketExecutionRailModel({
      t,
      selectedSymbol: 'BTCUSDT',
      nowMs: 1_000_000,
      preparedSelection,
    })

    expect(model.state).toBe('stale')
    expect(model.staleHint).toBe('workspace.market.executionRailStale')
  })
})
