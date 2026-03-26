import type { TranslationKey } from '../i18n/messages'
import type { DomainStatusMap, WorkspaceId } from '../store/slices/shared'
import type { OrderTimelineEvent } from '../types/contracts'

type Translate = (key: TranslationKey) => string

export type WorkspaceSummaryModel = {
  id: WorkspaceId
  titleKey: TranslationKey
  descriptionKey: TranslationKey
}

export type HealthCardModel = {
  id: string
  title: string
  stateLabel: string
  state: 'idle' | 'loading' | 'ready' | 'degraded' | 'error'
  staleLabel: string
  updatedAt: string
  requestId?: string
  reason?: string
}

export type ExecutionFeedRowModel = {
  id: string
  title: string
  subtitle: string
  rightTop: string
  rightBottom: string
}

export const WORKSPACE_MODELS: WorkspaceSummaryModel[] = [
  {
    id: 'overview',
    titleKey: 'workspace.overview.title',
    descriptionKey: 'workspace.overview.description',
  },
  {
    id: 'market',
    titleKey: 'workspace.market.title',
    descriptionKey: 'workspace.market.description',
  },
  {
    id: 'execution',
    titleKey: 'workspace.execution.title',
    descriptionKey: 'workspace.execution.description',
  },
  {
    id: 'health',
    titleKey: 'workspace.health.title',
    descriptionKey: 'workspace.health.description',
  },
]

function formatDateTime(value?: number | string | null): string {
  if (!value) {
    return '—'
  }
  const parsed = typeof value === 'number' ? value : Date.parse(value)
  if (Number.isNaN(parsed)) {
    return typeof value === 'string' ? value : '—'
  }
  return new Date(parsed).toLocaleString()
}

export function formatRequestLabel(value?: string | null): string {
  return value?.trim() ? value : '—'
}

export function formatNumber(value?: number | null, digits = 2): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '—'
  }
  return value.toFixed(digits)
}

export function formatPrice(value?: string | null): string {
  return value?.trim() ? value : '—'
}

export function formatConfidence(value?: number | null): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '0.000000'
  }
  return value.toFixed(6)
}

export function buildHealthCards(domainStatus: DomainStatusMap, t: Translate): HealthCardModel[] {
  return (Object.entries(domainStatus) as Array<[keyof DomainStatusMap, DomainStatusMap[keyof DomainStatusMap]]>).map(
    ([id, value]) => ({
      id,
      title:
        id === 'market-stream'
          ? t('health.domain.market')
          : id === 'strategy-summary'
            ? t('health.domain.strategy')
            : t('health.domain.execution'),
      state: value.state,
      stateLabel:
        value.state === 'loading'
          ? t('health.state.loading')
          : value.state === 'ready'
            ? t('health.state.ready')
            : value.state === 'degraded'
              ? t('health.state.degraded')
              : value.state === 'error'
                ? t('health.state.error')
                : t('health.state.idle'),
      staleLabel: value.stale ? t('health.stale') : t('health.fresh'),
      updatedAt: formatDateTime(value.last_update_ms),
      requestId: value.request_id,
      reason: value.reason,
    }),
  )
}

export function buildExecutionRows(events: OrderTimelineEvent[], t: Translate): ExecutionFeedRowModel[] {
  return events.map((event) => ({
    id: event.id,
    title: event.event_type,
    subtitle: [event.symbol ?? '—', event.account_id ?? '—'].join(' · '),
    rightTop: event.status ?? '—',
    rightBottom: `${t('execution.receivedAt')}: ${formatDateTime(event.received_at)}`,
  }))
}

export function summarizeLatestFeedback(event: OrderTimelineEvent | undefined, heartbeat: string | undefined, t: Translate) {
  if (!event) {
    return heartbeat ?? t('common.heartbeat')
  }
  return `${event.event_type} · ${event.symbol ?? '—'} · ${event.status ?? '—'}`
}

export function summarizeLatestEventAt(event: OrderTimelineEvent | undefined) {
  return formatDateTime(event?.event_time ?? event?.received_at)
}
