import type { OrderEvent, OrderTimelineEvent } from '../../../types/contracts'

let eventCounter = 0

function asString(value: unknown): string | undefined {
  if (typeof value !== 'string') {
    return undefined
  }
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : undefined
}

function asObject(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null
  }
  return value as Record<string, unknown>
}

export function normalizeOrderEvent(raw: OrderEvent): OrderTimelineEvent {
  const envelope = asObject(raw.payload)
  const envelopePayload = asObject(envelope?.payload)
  const payload = envelopePayload ?? envelope ?? {}
  const nestedOrder = asObject(payload.order)
  const nestedExecution = asObject(payload.execution)

  const symbol =
    asString(payload.symbol) ??
    asString(nestedOrder?.symbol) ??
    asString(nestedExecution?.symbol) ??
    undefined

  const accountId =
    asString(payload.account_id) ??
    asString(payload.accountId) ??
    asString(nestedOrder?.account_id) ??
    asString(nestedExecution?.account_id) ??
    undefined

  const orderId =
    asString(payload.order_id) ??
    asString(payload.orderId) ??
    asString(nestedOrder?.order_id) ??
    asString(nestedExecution?.order_id) ??
    undefined

  const requestId =
    asString(payload.request_id) ??
    asString(payload.requestId) ??
    asString(envelope?.request_id) ??
    asString(envelope?.correlation_id) ??
    asString((asObject(payload.error) ?? {}).request_id) ??
    undefined

  const eventType =
    asString(envelope?.event_type) ??
    asString(payload.event) ??
    asString(payload.type) ??
    asString(payload.signal) ??
    asString(nestedExecution?.event) ??
    raw.channel

  const status =
    asString(payload.status) ??
    asString(nestedOrder?.status) ??
    asString(nestedExecution?.status) ??
    undefined
  const eventTime =
    asString(payload.event_time) ??
    asString(payload.eventTime) ??
    asString(nestedExecution?.event_time) ??
    asString(nestedExecution?.eventTime) ??
    undefined

  eventCounter += 1
  return {
    id: `${raw.received_at}-${eventCounter}`,
    channel: raw.channel,
    payload,
    received_at: raw.received_at,
    event_time: eventTime,
    event_type: eventType,
    symbol,
    account_id: accountId,
    order_id: orderId,
    status,
    request_id: requestId,
  }
}

type RawSocketPayload = {
  type?: string
  message?: string
  channel?: string
  payload?: Record<string, unknown>
  received_at?: number
}

export type ParsedOrdersSocketMessage =
  | { kind: 'heartbeat'; message: string }
  | { kind: 'event'; event: OrderTimelineEvent }
  | { kind: 'raw'; message: string }
  | { kind: 'ignore' }

export function parseOrdersSocketMessage(data: string): ParsedOrdersSocketMessage {
  try {
    const payload = JSON.parse(data) as RawSocketPayload

    if (payload.type === 'heartbeat') {
      return { kind: 'heartbeat', message: payload.message ?? 'orders stream alive' }
    }

    if (payload.channel && payload.payload && typeof payload.received_at === 'number') {
      return {
        kind: 'event',
        event: normalizeOrderEvent({
          channel: payload.channel,
          payload: payload.payload,
          received_at: payload.received_at,
        }),
      }
    }

    return { kind: 'ignore' }
  } catch {
    return { kind: 'raw', message: data }
  }
}
