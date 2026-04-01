import { describe, expect, it } from 'vitest'

import type { OrderTimelineEvent } from '../types/contracts'
import {
  buildPreparedExecutionTimelineWindow,
  buildPreparedExecutionTimeline,
  filterPreparedExecutionTimeline,
  getExecutionTimelineWindowAnchor,
} from './execution-timeline'

function event(overrides: Partial<OrderTimelineEvent>): OrderTimelineEvent {
  return {
    id: 'evt',
    channel: 'trade.executions.default',
    payload: {},
    received_at: 1_712_000_000_000,
    event_type: 'execution.created',
    lifecycle_phase: 'submit',
    correlation_key: 'corr-1',
    ...overrides,
  }
}

describe('execution timeline view model', () => {
  it('prepares stable options and caches by event batch', () => {
    const events = [
      event({ id: '1', symbol: 'BTCUSDT', account_id: 'acct-a', status: 'accepted' }),
      event({ id: '2', symbol: 'ETHUSDT', account_id: 'acct-b', status: 'rejected' }),
    ]

    const first = buildPreparedExecutionTimeline(events)
    const second = buildPreparedExecutionTimeline(events)

    expect(first).toBe(second)
    expect(first.symbolOptions).toEqual(['ALL', 'BTCUSDT', 'ETHUSDT'])
    expect(first.accountOptions).toEqual(['ALL', 'acct-a', 'acct-b'])
    expect(first.statusOptions).toEqual(['ALL', 'accepted', 'rejected'])
  })

  it('replays filtered candidates from prepared indexes before keyword search', () => {
    const events = [
      event({
        id: '1',
        symbol: 'BTCUSDT',
        account_id: 'acct-a',
        status: 'accepted',
        request_id: 'req-1',
      }),
      event({
        id: '2',
        symbol: 'BTCUSDT',
        account_id: 'acct-b',
        status: 'rejected',
        request_id: 'req-2',
        reason: 'risk_limit',
      }),
      event({
        id: '3',
        symbol: 'ETHUSDT',
        account_id: 'acct-b',
        status: 'rejected',
        request_id: 'req-3',
      }),
    ]

    const prepared = buildPreparedExecutionTimeline(events)

    expect(
      filterPreparedExecutionTimeline({
        prepared,
        filterSymbol: 'BTCUSDT',
        filterAccountId: 'acct-b',
        filterStatus: 'rejected',
        keyword: '',
      }),
    ).toEqual([1])

    expect(
      filterPreparedExecutionTimeline({
        prepared,
        filterSymbol: 'ALL',
        filterAccountId: 'acct-b',
        filterStatus: 'rejected',
        keyword: 'risk_limit',
      }),
    ).toEqual([1])
  })

  it('derives a stable window anchor from scroll offsets', () => {
    expect(getExecutionTimelineWindowAnchor(0, 156, 6)).toBe(0)
    expect(getExecutionTimelineWindowAnchor(155, 156, 6)).toBe(0)
    expect(getExecutionTimelineWindowAnchor(1_560, 156, 6)).toBe(4)
  })

  it('builds a virtual window from prepared row indexes', () => {
    const window = buildPreparedExecutionTimelineWindow({
      rowIndexes: [0, 1, 2, 3, 4, 5, 6, 7],
      viewportHeight: 312,
      rowHeight: 156,
      overscanRows: 1,
      anchorIndex: 2,
    })

    expect(window.startIndex).toBe(2)
    expect(window.endIndex).toBe(6)
    expect(window.topSpacerHeight).toBe(312)
    expect(window.bottomSpacerHeight).toBe(312)
    expect(window.visibleRowIndexes).toEqual([2, 3, 4, 5])
  })
})
