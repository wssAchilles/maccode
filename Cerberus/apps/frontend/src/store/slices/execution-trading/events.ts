import type { OrderEvent, OrderTimelineEvent } from '../../../types/contracts'

let eventCounter = 0

function asString(value: unknown): string | undefined {
  if (typeof value !== 'string') {
    return undefined
  }
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : undefined
}

function asNumber(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string' && value.trim().length > 0) {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) {
      return parsed
    }
  }
  return undefined
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

  const clientOrderId =
    asString(payload.client_order_id) ??
    asString(payload.clientOrderId) ??
    asString(nestedOrder?.client_order_id) ??
    asString(nestedOrder?.clientOrderId) ??
    undefined

  const executionId =
    asString(payload.execution_id) ??
    asString(payload.executionId) ??
    asString(nestedExecution?.execution_id) ??
    asString(nestedExecution?.executionId) ??
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
  const reason =
    asString(payload.reason) ??
    asString(payload.message) ??
    asString((asObject(payload.error) ?? {}).message) ??
    undefined
  const side =
    asString(payload.side) ??
    asString(payload.signal) ??
    asString(nestedOrder?.side) ??
    undefined
  const price =
    asNumber(payload.price) ??
    asNumber(nestedOrder?.price) ??
    asNumber(nestedExecution?.price) ??
    undefined
  const quantity =
    asNumber(payload.quantity) ??
    asNumber(nestedOrder?.quantity) ??
    asNumber(nestedExecution?.quantity) ??
    undefined
  const filledQuantity =
    asNumber(payload.filled_quantity) ??
    asNumber(payload.filledQuantity) ??
    asNumber(nestedOrder?.filled_quantity) ??
    undefined
  const eventTime =
    asString(payload.event_time) ??
    asString(payload.eventTime) ??
    asString(nestedExecution?.event_time) ??
    asString(nestedExecution?.eventTime) ??
    undefined
  const lifecyclePhase = deriveLifecyclePhase({
    eventType,
    status,
    reason,
  })
  const correlationKey =
    executionId ??
    orderId ??
    clientOrderId ??
    requestId ??
    `${raw.channel}-${raw.received_at}`

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
    client_order_id: clientOrderId,
    execution_id: executionId,
    status,
    request_id: requestId,
    side,
    reason,
    price,
    quantity,
    filled_quantity: filledQuantity,
    lifecycle_phase: lifecyclePhase,
    correlation_key: correlationKey,
  }
}

function deriveLifecyclePhase({
  eventType,
  status,
  reason,
}: {
  eventType?: string
  status?: string
  reason?: string
}) {
  const normalizedStatus = `${status ?? ''}`.trim().toLowerCase()
  const normalizedType = `${eventType ?? ''}`.trim().toLowerCase()
  const normalizedReason = `${reason ?? ''}`.trim().toLowerCase()

  if (normalizedType.includes('cancel.requested') || normalizedStatus === 'cancel_requested') {
    return 'cancel_requested' as const
  }
  if (normalizedStatus === 'filled' || normalizedType.includes('execution.filled')) {
    return 'fill' as const
  }
  if (normalizedStatus === 'partial_fill' || normalizedStatus === 'partially_filled') {
    return 'partial_fill' as const
  }
  if (normalizedStatus === 'canceled' || normalizedStatus === 'cancelled') {
    return 'canceled' as const
  }
  if (normalizedStatus === 'rejected' || normalizedReason.length > 0) {
    return 'rejected' as const
  }
  if (normalizedStatus === 'accepted') {
    return 'accepted' as const
  }
  return 'submit' as const
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
