import type { TranslationKey } from '../i18n/messages'
import type { DomainStatusMap, WorkspaceId } from '../store/slices/shared'
import type { MarketMessage, OrderTimelineEvent, StrategySignal } from '../types/contracts'

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

export type WorkspaceSpotlightMetricModel = {
  id: string
  label: string
  value: string
  hint?: string
  tone?: 'default' | 'positive' | 'negative' | 'accent'
}

export type WorkspaceSpotlightModel = {
  summary: string
  hint?: string
  chips: string[]
  metrics: WorkspaceSpotlightMetricModel[]
}

export type PreparedTradingSnapshot = {
  selectedSymbol: string
  displayQuote?: MarketMessage
  bestBidValue: string
  bestAskValue: string
  midPriceValue: string
  spreadValue: string
  signalValue: string
  confidenceValue: string
  feedbackValue?: string
  feedbackAtValue: string
  quoteUpdatedAtValue: string
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

export function formatDerivedPrice(value?: number | null, digits = 6): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '—'
  }
  return value.toFixed(digits)
}

export function formatConfidence(value?: number | null): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '0.000000'
  }
  return value.toFixed(6)
}

export function parseNumericString(value?: string | null): number | undefined {
  if (!value?.trim()) {
    return undefined
  }
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : undefined
}

export function selectDisplayQuote(
  selectedSymbol: string,
  latest: MarketMessage | undefined,
  latestBySymbol: Record<string, MarketMessage | undefined>,
): MarketMessage | undefined {
  return latestBySymbol[selectedSymbol] ?? latest
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
    title: `${event.event_type} · ${event.lifecycle_phase}`,
    subtitle: [event.symbol ?? '—', event.account_id ?? '—', event.client_order_id ?? event.request_id ?? '—'].join(' · '),
    rightTop: event.status ?? event.lifecycle_phase,
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

export function summarizeDomainStates(domainStatus: DomainStatusMap) {
  let readyCount = 0
  let attentionCount = 0

  for (const status of Object.values(domainStatus)) {
    if (status.state === 'ready' && !status.stale) {
      readyCount += 1
      continue
    }
    if (status.state === 'degraded' || status.state === 'error' || status.stale) {
      attentionCount += 1
    }
  }

  return {
    readyCount,
    attentionCount,
    totalCount: Object.keys(domainStatus).length,
  }
}

export function buildPreparedTradingSnapshot({
  selectedSymbol,
  latest,
  latestBySymbol,
  strategySignal,
  latestEvent,
  heartbeat,
}: {
  selectedSymbol: string
  latest?: MarketMessage
  latestBySymbol: Record<string, MarketMessage | undefined>
  strategySignal?: StrategySignal
  latestEvent?: OrderTimelineEvent
  heartbeat?: string
}): PreparedTradingSnapshot {
  const displayQuote = selectDisplayQuote(selectedSymbol, latest, latestBySymbol)
  const bid = parseNumericString(displayQuote?.bid_price)
  const ask = parseNumericString(displayQuote?.ask_price)
  const spread = bid !== undefined && ask !== undefined ? ask - bid : undefined
  const midPrice = bid !== undefined && ask !== undefined ? (bid + ask) / 2 : undefined

  return {
    selectedSymbol,
    displayQuote,
    bestBidValue: formatPrice(displayQuote?.bid_price),
    bestAskValue: formatPrice(displayQuote?.ask_price),
    midPriceValue: formatDerivedPrice(midPrice),
    spreadValue: formatDerivedPrice(spread),
    signalValue: strategySignal?.signal ?? 'HOLD',
    confidenceValue: formatConfidence(strategySignal?.confidence),
    feedbackValue: latestEvent
      ? `${latestEvent.event_type} · ${latestEvent.symbol ?? '—'} · ${latestEvent.status ?? '—'}`
      : heartbeat,
    feedbackAtValue: summarizeLatestEventAt(latestEvent),
    quoteUpdatedAtValue: formatDateTime(displayQuote?.event_time),
  }
}
