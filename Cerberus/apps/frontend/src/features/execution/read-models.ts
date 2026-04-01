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

export type PreparedExecutionSelection = {
  orderModels: ExecutionOrderReadModel[]
  latestOrder?: ExecutionOrderReadModel
  latestTimestamp?: number
  latestAnomaly?: ExecutionOrderReadModel
  lifecycleDistribution: ExecutionLifecycleDistribution
  anomalySummary: ExecutionAnomalySummary
  accountSummary: ExecutionAccountSummary[]
  activeOrderCount: number
  acceptedCount: number
  partialFillCount: number
  filledCount: number
  rejectedCount: number
  canceledCount: number
}

type PreparedOrderReadModels = {
  all: ExecutionOrderReadModel[]
  bySymbol: Map<string, ExecutionOrderReadModel[]>
}

const preparedOrderReadModelsCache = new WeakMap<OrderTimelineEvent[], PreparedOrderReadModels>()
const preparedExecutionSelectionCache = new WeakMap<OrderTimelineEvent[], Map<string, PreparedExecutionSelection>>()
const preparedExecutionSummaryCache = new WeakMap<ExecutionOrderReadModel[], Omit<PreparedExecutionSelection, 'orderModels'>>()
const preparedMarkersCache = new WeakMap<OrderTimelineEvent[], Map<string, ExecutionMarker[]>>()

function eventTimestamp(event: OrderTimelineEvent): number {
  if (event.event_time) {
    const parsed = Date.parse(event.event_time)
    if (!Number.isNaN(parsed)) {
      return parsed
    }
  }
  const receivedAt = event.received_at as number | string
  if (typeof receivedAt === 'string') {
    const parsed = Date.parse(receivedAt)
    if (!Number.isNaN(parsed)) {
      return parsed
    }
    const fallback = Number(receivedAt)
    if (!Number.isNaN(fallback)) {
      return fallback
    }
    return 0
  }
  return receivedAt
}

function latestPhase(events: OrderTimelineEvent[]): ExecutionLifecyclePhase {
  return [...events]
    .sort((left, right) => eventTimestamp(right) - eventTimestamp(left))[0]?.lifecycle_phase ?? 'submit'
}

export function buildExecutionOrderReadModels(events: OrderTimelineEvent[], symbol?: string): ExecutionOrderReadModel[] {
  let prepared = preparedOrderReadModelsCache.get(events)

  if (!prepared) {
    const groups = new Map<string, OrderTimelineEvent[]>()
    for (const event of events) {
      const current = groups.get(event.correlation_key) ?? []
      current.push(event)
      groups.set(event.correlation_key, current)
    }

    const all = [...groups.entries()]
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

    const bySymbol = new Map<string, ExecutionOrderReadModel[]>()
    for (const model of all) {
      const key = model.symbol ?? ''
      const current = bySymbol.get(key) ?? []
      current.push(model)
      bySymbol.set(key, current)
    }

    prepared = { all, bySymbol }
    preparedOrderReadModelsCache.set(events, prepared)
  }

  if (!symbol) {
    return prepared.all
  }

  return prepared.bySymbol.get(symbol) ?? []
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

function prepareExecutionSelectionSummary(
  orderModels: ExecutionOrderReadModel[],
): Omit<PreparedExecutionSelection, 'orderModels'> {
  const cached = preparedExecutionSummaryCache.get(orderModels)
  if (cached) {
    return cached
  }

  const lifecycleDistribution: ExecutionLifecycleDistribution = {
    submit: 0,
    accepted: 0,
    rejected: 0,
    partial_fill: 0,
    fill: 0,
    cancel_requested: 0,
    canceled: 0,
  }
  const rejectionCounts = new Map<string, number>()
  const cancelFailureCounts = new Map<string, number>()
  const accountGroups = new Map<string, ExecutionAccountSummary>()
  const latestAccountTimestamps = new Map<string, number>()
  const submitToAccepted: number[] = []
  const submitToFill: number[] = []
  const slippageBps: number[] = []

  let latestOrder: ExecutionOrderReadModel | undefined
  let latestTimestamp: number | undefined
  let latestAnomaly: ExecutionOrderReadModel | undefined
  let activeOrderCount = 0
  let partialFillCount = 0
  let cancelFailures = 0

  for (const model of orderModels) {
    lifecycleDistribution[model.latestPhase] += 1

    if (!latestOrder) {
      latestOrder = model
      latestTimestamp = rightMostTimestamp(model.events)
    }

    if (!latestAnomaly && (model.latestPhase === 'rejected' || model.latestPhase === 'canceled')) {
      latestAnomaly = model
    }

    if (model.latestPhase === 'rejected' && model.latestReason) {
      rejectionCounts.set(model.latestReason, (rejectionCounts.get(model.latestReason) ?? 0) + 1)
    }
    if (model.latestPhase === 'partial_fill') {
      partialFillCount += 1
    }
    if (['submit', 'accepted', 'partial_fill', 'cancel_requested'].includes(model.latestPhase)) {
      activeOrderCount += 1
    }
    if (model.cancelRequestedAt && !model.canceledAt) {
      cancelFailures += 1
      const reason = model.latestReason ?? 'cancel_pending'
      cancelFailureCounts.set(reason, (cancelFailureCounts.get(reason) ?? 0) + 1)
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

    const accountId = model.accountId ?? 'unknown'
    const current =
      accountGroups.get(accountId) ??
      {
        accountId,
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
    const knownTimestamp = latestAccountTimestamps.get(accountId) ?? -1
    if (candidateTimestamp >= knownTimestamp) {
      current.latestPhase = model.latestPhase
      latestAccountTimestamps.set(accountId, candidateTimestamp)
    }
    accountGroups.set(accountId, current)
  }

  const prepared = {
    latestOrder,
    latestTimestamp,
    latestAnomaly,
    lifecycleDistribution,
    anomalySummary: {
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
      partialFillRatio: orderModels.length > 0 ? partialFillCount / orderModels.length : undefined,
    },
    accountSummary: [...accountGroups.values()].sort(
      (left, right) => right.observed - left.observed || left.accountId.localeCompare(right.accountId),
    ),
    activeOrderCount,
    acceptedCount: lifecycleDistribution.accepted,
    partialFillCount,
    filledCount: lifecycleDistribution.fill,
    rejectedCount: lifecycleDistribution.rejected,
    canceledCount: lifecycleDistribution.canceled,
  }

  preparedExecutionSummaryCache.set(orderModels, prepared)
  return prepared
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
  return prepareExecutionSelectionSummary(models).anomalySummary
}

export function buildExecutionAccountSummaries(models: ExecutionOrderReadModel[]): ExecutionAccountSummary[] {
  return prepareExecutionSelectionSummary(models).accountSummary
}

export function buildExecutionLifecycleDistribution(
  models: ExecutionOrderReadModel[],
): ExecutionLifecycleDistribution {
  return prepareExecutionSelectionSummary(models).lifecycleDistribution
}

export function buildPreparedExecutionSelection(
  events: OrderTimelineEvent[],
  symbol?: string,
): PreparedExecutionSelection {
  let preparedBySymbol = preparedExecutionSelectionCache.get(events)
  if (!preparedBySymbol) {
    preparedBySymbol = new Map<string, PreparedExecutionSelection>()
    preparedExecutionSelectionCache.set(events, preparedBySymbol)
  }

  const symbolKey = symbol ?? '__all__'
  const cached = preparedBySymbol.get(symbolKey)
  if (cached) {
    return cached
  }

  const orderModels = buildExecutionOrderReadModels(events, symbol)
  const prepared = {
    orderModels,
    ...prepareExecutionSelectionSummary(orderModels),
  }
  preparedBySymbol.set(symbolKey, prepared)
  return prepared
}

export type ExecutionMarker = {
  id: string
  time: number
  phase: ExecutionLifecyclePhase
  label: string
  tone: 'positive' | 'negative' | 'accent' | 'muted'
}

export function buildExecutionMarkers(events: OrderTimelineEvent[], symbol: string): ExecutionMarker[] {
  let prepared = preparedMarkersCache.get(events)

  if (!prepared) {
    prepared = new Map<string, ExecutionMarker[]>()
    for (const item of events) {
      if (!item.symbol) {
        continue
      }
      const tone: ExecutionMarker['tone'] =
        item.lifecycle_phase === 'fill'
          ? 'positive'
          : item.lifecycle_phase === 'rejected'
            ? 'negative'
            : item.lifecycle_phase === 'partial_fill'
              ? 'accent'
              : 'muted'
      const current = prepared.get(item.symbol) ?? []
      current.push({
        id: item.id,
        time: eventTimestamp(item),
        phase: item.lifecycle_phase,
        label: item.execution_id ?? item.request_id ?? item.status ?? item.lifecycle_phase,
        tone,
      })
      prepared.set(item.symbol, current)
    }

    for (const [preparedSymbol, current] of prepared.entries()) {
      prepared.set(
        preparedSymbol,
        current
          .slice()
          .sort((left, right) => left.time - right.time)
          .slice(0, 8),
      )
    }

    preparedMarkersCache.set(events, prepared)
  }

  return prepared.get(symbol) ?? []
}
