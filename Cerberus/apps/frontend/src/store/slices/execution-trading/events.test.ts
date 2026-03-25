import { describe, expect, it } from 'vitest'

import { normalizeOrderEvent, parseOrdersSocketMessage } from './events'

describe('normalizeOrderEvent', () => {
  it('extracts canonical fields for timeline', () => {
    const normalized = normalizeOrderEvent({
      channel: 'trade.executions.default',
      received_at: 1_710_000_000_000,
      payload: {
        event: 'matching.execution.filled',
        account_id: 'default',
        order_id: 'ord-001',
        symbol: 'BTCUSDT',
        status: 'filled',
        request_id: 'rid-001',
        event_time: '2026-03-25T12:00:00+00:00',
      },
    })

    expect(normalized.event_type).toBe('matching.execution.filled')
    expect(normalized.account_id).toBe('default')
    expect(normalized.order_id).toBe('ord-001')
    expect(normalized.symbol).toBe('BTCUSDT')
    expect(normalized.status).toBe('filled')
    expect(normalized.request_id).toBe('rid-001')
    expect(normalized.event_time).toBe('2026-03-25T12:00:00+00:00')
  })
})

describe('parseOrdersSocketMessage', () => {
  it('parses heartbeat frames', () => {
    const parsed = parseOrdersSocketMessage(
      JSON.stringify({ type: 'heartbeat', message: 'orders stream alive' }),
    )
    expect(parsed.kind).toBe('heartbeat')
    if (parsed.kind === 'heartbeat') {
      expect(parsed.message).toBe('orders stream alive')
    }
  })

  it('parses event frames and normalizes payload', () => {
    const parsed = parseOrdersSocketMessage(
      JSON.stringify({
        channel: 'trade.executions.default',
        received_at: 1_710_000_000_000,
        payload: {
          event: 'matching.order.submitted',
          account_id: 'default',
          order_id: 'ord-101',
          symbol: 'ETHUSDT',
          status: 'submitted',
          request_id: 'rid-101',
          event_time: '2026-03-25T12:01:00+00:00',
        },
      }),
    )
    expect(parsed.kind).toBe('event')
    if (parsed.kind === 'event') {
      expect(parsed.event.order_id).toBe('ord-101')
      expect(parsed.event.request_id).toBe('rid-101')
      expect(parsed.event.status).toBe('submitted')
      expect(parsed.event.event_time).toBe('2026-03-25T12:01:00+00:00')
    }
  })
})
