import type { OrderTimelineEvent } from '../types/contracts'
import { formatDateTimeLabel, formatEmptyStateLabel, formatRequestLabel } from './workbench'

export type PreparedExecutionTimelineRow = {
  id: string
  event: OrderTimelineEvent
  title: string
  subtitle: string
  rightTop: string
  receivedAtLabel: string
  eventTimeLabel: string
  orderIdLabel: string
  requestIdLabel: string
  clientOrderIdLabel: string
  executionIdLabel: string
  searchText: string
}

export type PreparedExecutionTimeline = {
  rows: PreparedExecutionTimelineRow[]
  allRowIndexes: number[]
  symbolOptions: string[]
  accountOptions: string[]
  statusOptions: string[]
  bySymbol: Map<string, number[]>
  byAccount: Map<string, number[]>
  byStatus: Map<string, number[]>
}

export type PreparedExecutionTimelineWindow = {
  startIndex: number
  endIndex: number
  topSpacerHeight: number
  bottomSpacerHeight: number
  visibleRowIndexes: number[]
}

const preparedExecutionTimelineCache = new WeakMap<OrderTimelineEvent[], PreparedExecutionTimeline>()

function pushIndex(map: Map<string, number[]>, key: string | undefined, index: number) {
  if (!key) {
    return
  }
  const current = map.get(key) ?? []
  current.push(index)
  map.set(key, current)
}

function intersectSorted(left: number[], right: number[]): number[] {
  if (left.length === 0 || right.length === 0) {
    return []
  }

  let leftIndex = 0
  let rightIndex = 0
  const intersection: number[] = []

  while (leftIndex < left.length && rightIndex < right.length) {
    const leftValue = left[leftIndex]
    const rightValue = right[rightIndex]
    if (leftValue === rightValue) {
      intersection.push(leftValue)
      leftIndex += 1
      rightIndex += 1
      continue
    }
    if (leftValue < rightValue) {
      leftIndex += 1
      continue
    }
    rightIndex += 1
  }

  return intersection
}

function formatCompactIdentifier(
  value: string | null | undefined,
  kind: 'request-id' | 'order-id' | 'client-order-id' | 'execution-id' = 'request-id',
): string {
  const normalized = formatRequestLabel(value, formatEmptyStateLabel(kind))
  if (normalized === formatEmptyStateLabel(kind) || normalized.length <= 28) {
    return normalized
  }
  return `${normalized.slice(0, 16)}…${normalized.slice(-8)}`
}

export function buildPreparedExecutionTimeline(orderEvents: OrderTimelineEvent[]): PreparedExecutionTimeline {
  const cached = preparedExecutionTimelineCache.get(orderEvents)
  if (cached) {
    return cached
  }

  const rows: PreparedExecutionTimelineRow[] = []
  const symbols = new Set<string>()
  const accounts = new Set<string>()
  const statuses = new Set<string>()
  const bySymbol = new Map<string, number[]>()
  const byAccount = new Map<string, number[]>()
  const byStatus = new Map<string, number[]>()

  for (const event of orderEvents) {
    const rowIndex = rows.length
    if (event.symbol) {
      symbols.add(event.symbol)
    }
    if (event.account_id) {
      accounts.add(event.account_id)
    }
    if (event.status) {
      statuses.add(event.status)
    }

    pushIndex(bySymbol, event.symbol, rowIndex)
    pushIndex(byAccount, event.account_id, rowIndex)
    pushIndex(byStatus, event.status, rowIndex)

    rows.push({
      id: event.id,
      event,
      title: `${event.event_type} · ${event.lifecycle_phase}`,
      subtitle: [
        formatRequestLabel(event.symbol),
        formatRequestLabel(event.account_id),
        formatRequestLabel(event.client_order_id ?? event.request_id, formatEmptyStateLabel('request-id')),
      ].join(' · '),
      rightTop: event.status ?? event.lifecycle_phase,
      receivedAtLabel: formatDateTimeLabel(event.received_at),
      eventTimeLabel: formatDateTimeLabel(event.event_time),
      orderIdLabel: formatCompactIdentifier(event.order_id, 'order-id'),
      requestIdLabel: formatCompactIdentifier(event.request_id, 'request-id'),
      clientOrderIdLabel: formatCompactIdentifier(event.client_order_id, 'client-order-id'),
      executionIdLabel: formatCompactIdentifier(event.execution_id, 'execution-id'),
      searchText: [
        event.symbol,
        event.account_id,
        event.status,
        event.order_id,
        event.request_id,
        event.client_order_id,
        event.execution_id,
        event.lifecycle_phase,
        event.event_type,
        event.reason,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase(),
    })
  }

  const prepared = {
    rows,
    allRowIndexes: rows.map((_, index) => index),
    symbolOptions: ['ALL', ...Array.from(symbols).sort()],
    accountOptions: ['ALL', ...Array.from(accounts).sort()],
    statusOptions: ['ALL', ...Array.from(statuses).sort()],
    bySymbol,
    byAccount,
    byStatus,
  }

  preparedExecutionTimelineCache.set(orderEvents, prepared)
  return prepared
}

export function filterPreparedExecutionTimeline({
  prepared,
  filterSymbol,
  filterAccountId,
  filterStatus,
  keyword,
}: {
  prepared: PreparedExecutionTimeline
  filterSymbol: string
  filterAccountId: string
  filterStatus: string
  keyword: string
}): number[] {
  let candidates = prepared.allRowIndexes

  if (filterSymbol !== 'ALL') {
    candidates = prepared.bySymbol.get(filterSymbol) ?? []
  }
  if (filterAccountId !== 'ALL') {
    const accountCandidates = prepared.byAccount.get(filterAccountId) ?? []
    candidates = candidates === prepared.allRowIndexes ? accountCandidates : intersectSorted(candidates, accountCandidates)
  }
  if (filterStatus !== 'ALL') {
    const statusCandidates = prepared.byStatus.get(filterStatus) ?? []
    candidates = candidates === prepared.allRowIndexes ? statusCandidates : intersectSorted(candidates, statusCandidates)
  }

  const trimmedKeyword = keyword.trim().toLowerCase()
  if (trimmedKeyword.length === 0) {
    return candidates
  }

  return candidates.filter((index) => prepared.rows[index]?.searchText.includes(trimmedKeyword))
}

export function getExecutionTimelineWindowAnchor(
  scrollTop: number,
  rowHeight: number,
  overscanRows: number,
): number {
  if (rowHeight <= 0) {
    return 0
  }
  return Math.max(0, Math.floor(scrollTop / rowHeight) - overscanRows)
}

export function buildPreparedExecutionTimelineWindow({
  rowIndexes,
  viewportHeight,
  rowHeight,
  overscanRows,
  anchorIndex,
}: {
  rowIndexes: number[]
  viewportHeight: number
  rowHeight: number
  overscanRows: number
  anchorIndex: number
}): PreparedExecutionTimelineWindow {
  const visibleCount = Math.ceil(viewportHeight / rowHeight) + overscanRows * 2
  const startIndex = Math.max(0, Math.min(anchorIndex, rowIndexes.length))
  const endIndex = Math.min(rowIndexes.length, startIndex + visibleCount)

  return {
    startIndex,
    endIndex,
    topSpacerHeight: startIndex * rowHeight,
    bottomSpacerHeight: Math.max(0, (rowIndexes.length - endIndex) * rowHeight),
    visibleRowIndexes: rowIndexes.slice(startIndex, endIndex),
  }
}
