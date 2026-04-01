import { describe, expect, it } from 'vitest'

import type { OrderTimelineEvent } from '../../types/contracts'
import { buildPreparedExecutionSelection } from './read-models'

function event(overrides: Partial<OrderTimelineEvent>): OrderTimelineEvent {
  return {
    id: 'evt',
    channel: 'trade.executions.default',
    payload: {},
    received_at: '2026-03-31T08:00:00Z',
    event_type: 'execution.update',
    lifecycle_phase: 'submit',
    correlation_key: 'corr-1',
    ...overrides,
  }
}

describe('execution read models', () => {
  it('caches prepared execution selections per event batch and symbol', () => {
    const events = [
      event({
        id: 'submit-1',
        symbol: 'BTCUSDT',
        correlation_key: 'btc-1',
        lifecycle_phase: 'submit',
        request_id: 'req-1',
      }),
      event({
        id: 'fill-1',
        symbol: 'BTCUSDT',
        correlation_key: 'btc-1',
        lifecycle_phase: 'fill',
        execution_id: 'exec-1',
        status: 'filled',
        received_at: '2026-03-31T08:00:10Z',
      }),
      event({
        id: 'submit-2',
        symbol: 'ETHUSDT',
        correlation_key: 'eth-1',
        lifecycle_phase: 'accepted',
        request_id: 'req-2',
        received_at: '2026-03-31T08:01:00Z',
      }),
    ]

    const first = buildPreparedExecutionSelection(events, 'BTCUSDT')
    const second = buildPreparedExecutionSelection(events, 'BTCUSDT')
    const otherSymbol = buildPreparedExecutionSelection(events, 'ETHUSDT')

    expect(first).toBe(second)
    expect(first.orderModels).toBe(second.orderModels)
    expect(first.orderModels).toHaveLength(1)
    expect(otherSymbol.orderModels).toHaveLength(1)
  })

  it('prepares lifecycle, anomaly, and account summaries in one selection', () => {
    const events = [
      event({
        id: 'submit-1',
        symbol: 'BTCUSDT',
        correlation_key: 'ord-1',
        lifecycle_phase: 'submit',
        request_id: 'req-1',
        order_id: 'ord-1',
        account_id: 'acct-a',
        price: 100,
        quantity: 1,
      }),
      event({
        id: 'partial-1',
        symbol: 'BTCUSDT',
        correlation_key: 'ord-1',
        lifecycle_phase: 'partial_fill',
        execution_id: 'exec-1',
        account_id: 'acct-a',
        price: 101,
        quantity: 0.4,
        filled_quantity: 0.4,
        received_at: '2026-03-31T08:00:20Z',
      }),
      event({
        id: 'reject-1',
        symbol: 'BTCUSDT',
        correlation_key: 'ord-2',
        lifecycle_phase: 'rejected',
        request_id: 'req-2',
        order_id: 'ord-2',
        account_id: 'acct-b',
        reason: 'risk_limit',
        received_at: '2026-03-31T08:00:30Z',
      }),
      event({
        id: 'cancel-request-1',
        symbol: 'BTCUSDT',
        correlation_key: 'ord-3',
        lifecycle_phase: 'cancel_requested',
        request_id: 'req-3',
        order_id: 'ord-3',
        account_id: 'acct-a',
        reason: 'pending_cancel',
        received_at: '2026-03-31T08:00:40Z',
      }),
    ]

    const prepared = buildPreparedExecutionSelection(events, 'BTCUSDT')

    expect(prepared.latestOrder?.id).toBe('ord-3')
    expect(prepared.latestAnomaly?.id).toBe('ord-2')
    expect(prepared.activeOrderCount).toBe(2)
    expect(prepared.partialFillCount).toBe(1)
    expect(prepared.rejectedCount).toBe(1)
    expect(prepared.canceledCount).toBe(0)
    expect(prepared.lifecycleDistribution).toMatchObject({
      partial_fill: 1,
      rejected: 1,
      cancel_requested: 1,
    })
    expect(prepared.anomalySummary.rejectionReasons).toEqual([{ reason: 'risk_limit', count: 1 }])
    expect(prepared.anomalySummary.cancelFailureReasons).toEqual([{ reason: 'pending_cancel', count: 1 }])
    expect(prepared.anomalySummary.cancelFailures).toBe(1)
    expect(prepared.accountSummary[0]).toMatchObject({
      accountId: 'acct-a',
      observed: 2,
      partialFill: 1,
      active: 2,
    })
  })
})
