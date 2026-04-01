import type { ExecutionLifecyclePhase, OrderTimelineEvent } from '../../types/contracts'

export type ExecutionOrderReadModel = {
  id: string
  symbol?: string
  accountId?: string
  requestId?: string
  orderId?: string
  clientOrderId?: string
  executionIds: string[]
  side?: string
  price?: number
  quantity?: number
  filledQuantity: number
  latestPhase: ExecutionLifecyclePhase
  latestStatus?: string
  latestReason?: string
  submitAt?: number
  acceptedAt?: number
  fillAt?: number
  cancelRequestedAt?: number
  canceledAt?: number
  rejectedAt?: number
  averageExecutionPrice?: number
  eventCount: number
  events: OrderTimelineEvent[]
}

export type ExecutionAnomalySummary = {
  rejectionReasons: { reason: string; count: number }[]
  cancelFailureReasons: { reason: string; count: number }[]
  cancelFailures: number
  avgSubmitToAcceptedMs?: number
  avgSubmitToFillMs?: number
  fillSlippageBps?: number
  partialFillRatio?: number
}

export type ExecutionAccountSummary = {
  accountId: string
  observed: number
  accepted: number
  partialFill: number
  filled: number
  rejected: number
  canceled: number
  active: number
  latestPhase?: ExecutionLifecyclePhase
}

export type ExecutionLifecycleDistribution = Record<ExecutionLifecyclePhase, number>

function eventTimestamp(event: OrderTimelineEvent): number {
  if (event.event_time) {
    const parsed = Date.parse(event.event_time)
    if (!Number.isNaN(parsed)) {
      return parsed
    }
  }
  return event.received_at
}

function latestPhase(events: OrderTimelineEvent[]): ExecutionLifecyclePhase {
  return [...events]
    .sort((left, right) => eventTimestamp(right) - eventTimestamp(left))[0]?.lifecycle_phase ?? 'submit'
}

export function buildExecutionOrderReadModels(events: OrderTimelineEvent[], symbol?: string): ExecutionOrderReadModel[] {
  const filtered = symbol ? events.filter((item) => item.symbol === symbol) : events
  const groups = new Map<string, OrderTimelineEvent[]>()
  for (const event of filtered) {
    const current = groups.get(event.correlation_key) ?? []
    current.push(event)
    groups.set(event.correlation_key, current)
  }

  return [...groups.entries()]
    .map(([id, items]) => {
      const sorted = [...items].sort((left, right) => eventTimestamp(left) - eventTimestamp(right))
      const first = sorted[0]
      const latest = sorted[sorted.length - 1]
      const fills = sorted.filter((item) => item.lifecycle_phase === 'fill' || item.lifecycle_phase === 'partial_fill')
      const filledQuantity = fills.reduce((sum, item) => sum + (item.quantity ?? item.filled_quantity ?? 0), 0)
      const fillPriceWeight = fills.reduce(
        (sum, item) => sum + ((item.price ?? 0) * (item.quantity ?? item.filled_quantity ?? 0)),
        0,
      )
      const fillVolume = fills.reduce((sum, item) => sum + (item.quantity ?? item.filled_quantity ?? 0), 0)

      return {
        id,
        symbol: latest.symbol ?? first.symbol,
        accountId: latest.account_id ?? first.account_id,
        requestId: latest.request_id ?? first.request_id,
        orderId: latest.order_id ?? first.order_id,
        clientOrderId: latest.client_order_id ?? first.client_order_id,
        executionIds: sorted.map((item) => item.execution_id).filter((value): value is string => Boolean(value)),
        side: latest.side ?? first.side,
        price: latest.price ?? first.price,
        quantity: latest.quantity ?? first.quantity,
        filledQuantity,
        latestPhase: latestPhase(sorted),
        latestStatus: latest.status,
        latestReason: latest.reason,
        submitAt: timestampForFirstPhase(sorted, 'submit'),
        acceptedAt: timestampForFirstPhase(sorted, 'accepted'),
        fillAt: timestampForLastPhase(sorted, 'fill', 'partial_fill'),
        cancelRequestedAt: timestampForFirstPhase(sorted, 'cancel_requested'),
        canceledAt: timestampForLastPhase(sorted, 'canceled'),
        rejectedAt: timestampForLastPhase(sorted, 'rejected'),
        averageExecutionPrice: fillVolume > 0 ? fillPriceWeight / fillVolume : undefined,
        eventCount: sorted.length,
        events: sorted,
      }
    })
    .sort((left, right) => {
      const leftTime = rightMostTimestamp(left.events)
      const rightTime = rightMostTimestamp(right.events)
      return rightTime - leftTime
    })
}

function rightMostTimestamp(events: OrderTimelineEvent[]): number {
  return events.reduce((latest, item) => Math.max(latest, eventTimestamp(item)), 0)
}

function average(values: number[]): number | undefined {
  if (values.length === 0) {
    return undefined
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

function timestampForFirstPhase(events: OrderTimelineEvent[], ...phases: ExecutionLifecyclePhase[]): number | undefined {
  const hit = events.find((item) => phases.includes(item.lifecycle_phase))
  return hit ? eventTimestamp(hit) : undefined
}

function timestampForLastPhase(events: OrderTimelineEvent[], ...phases: ExecutionLifecyclePhase[]): number | undefined {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    if (phases.includes(events[index].lifecycle_phase)) {
      return eventTimestamp(events[index])
    }
  }
  return undefined
}

export function buildExecutionAnomalySummary(models: ExecutionOrderReadModel[]): ExecutionAnomalySummary {
  const rejectionCounts = new Map<string, number>()
  const cancelFailureCounts = new Map<string, number>()
  let cancelFailures = 0
  const submitToAccepted: number[] = []
  const submitToFill: number[] = []
  const slippageBps: number[] = []
  let partialFillOrders = 0

  for (const model of models) {
    if (model.latestPhase === 'rejected' && model.latestReason) {
      rejectionCounts.set(model.latestReason, (rejectionCounts.get(model.latestReason) ?? 0) + 1)
    }
    if (model.latestPhase === 'partial_fill') {
      partialFillOrders += 1
    }
    if (model.cancelRequestedAt && !model.canceledAt) {
      cancelFailures += 1
      cancelFailureCounts.set(
        model.latestReason ?? 'cancel_pending',
        (cancelFailureCounts.get(model.latestReason ?? 'cancel_pending') ?? 0) + 1,
      )
    }
    if (model.submitAt && model.acceptedAt && model.acceptedAt >= model.submitAt) {
      submitToAccepted.push(model.acceptedAt - model.submitAt)
    }
    if (model.submitAt && model.fillAt && model.fillAt >= model.submitAt) {
      submitToFill.push(model.fillAt - model.submitAt)
    }
    if (model.price && model.averageExecutionPrice && model.price > 0) {
      slippageBps.push(((model.averageExecutionPrice - model.price) / model.price) * 10_000)
    }
  }

  return {
    rejectionReasons: [...rejectionCounts.entries()]
      .map(([reason, count]) => ({ reason, count }))
      .sort((left, right) => right.count - left.count || left.reason.localeCompare(right.reason))
      .slice(0, 3),
    cancelFailureReasons: [...cancelFailureCounts.entries()]
      .map(([reason, count]) => ({ reason, count }))
      .sort((left, right) => right.count - left.count || left.reason.localeCompare(right.reason))
      .slice(0, 3),
    cancelFailures,
    avgSubmitToAcceptedMs: average(submitToAccepted),
    avgSubmitToFillMs: average(submitToFill),
    fillSlippageBps: average(slippageBps),
    partialFillRatio: models.length > 0 ? partialFillOrders / models.length : undefined,
  }
}

export function buildExecutionAccountSummaries(models: ExecutionOrderReadModel[]): ExecutionAccountSummary[] {
  const groups = new Map<string, ExecutionAccountSummary>()
  const latestTimestamps = new Map<string, number>()
  for (const model of models) {
    const key = model.accountId ?? 'unknown'
    const current =
      groups.get(key) ??
      {
        accountId: key,
        observed: 0,
        accepted: 0,
        partialFill: 0,
        filled: 0,
        rejected: 0,
        canceled: 0,
        active: 0,
        latestPhase: undefined,
      }
    current.observed += 1
    if (model.latestPhase === 'accepted') {
      current.accepted += 1
    }
    if (model.latestPhase === 'partial_fill') {
      current.partialFill += 1
    }
    if (model.latestPhase === 'fill') {
      current.filled += 1
    }
    if (model.latestPhase === 'rejected') {
      current.rejected += 1
    }
    if (model.latestPhase === 'canceled') {
      current.canceled += 1
    }
    if (['submit', 'accepted', 'partial_fill', 'cancel_requested'].includes(model.latestPhase)) {
      current.active += 1
    }
    const candidateTimestamp = rightMostTimestamp(model.events)
    const knownTimestamp = latestTimestamps.get(key) ?? -1
    if (candidateTimestamp >= knownTimestamp) {
      current.latestPhase = model.latestPhase
      latestTimestamps.set(key, candidateTimestamp)
    }
    groups.set(key, current)
  }
  return [...groups.values()].sort(
    (left, right) => right.observed - left.observed || left.accountId.localeCompare(right.accountId),
  )
}

export function buildExecutionLifecycleDistribution(
  models: ExecutionOrderReadModel[],
): ExecutionLifecycleDistribution {
  const distribution: ExecutionLifecycleDistribution = {
    submit: 0,
    accepted: 0,
    rejected: 0,
    partial_fill: 0,
    fill: 0,
    cancel_requested: 0,
    canceled: 0,
  }
  for (const model of models) {
    distribution[model.latestPhase] += 1
  }
  return distribution
}

export type ExecutionMarker = {
  id: string
  time: number
  phase: ExecutionLifecyclePhase
  label: string
  tone: 'positive' | 'negative' | 'accent' | 'muted'
}

export function buildExecutionMarkers(events: OrderTimelineEvent[], symbol: string): ExecutionMarker[] {
  return events
    .filter((item) => item.symbol === symbol)
    .slice(0, 8)
    .map((item) => {
      const tone: ExecutionMarker['tone'] =
        item.lifecycle_phase === 'fill'
          ? 'positive'
          : item.lifecycle_phase === 'rejected'
            ? 'negative'
            : item.lifecycle_phase === 'partial_fill'
              ? 'accent'
              : 'muted'
      return {
        id: item.id,
        time: eventTimestamp(item),
        phase: item.lifecycle_phase,
        label: item.execution_id ?? item.request_id ?? item.status ?? item.lifecycle_phase,
        tone,
      }
    })
    .sort((left, right) => left.time - right.time)
}
