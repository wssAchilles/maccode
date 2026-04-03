import type { TranslationKey } from '../i18n/messages'
import type { CoreFlowMap, CoreFlowStepId, CoreFlowStepState, DomainStatusMap, WorkspaceId } from '../store/slices/shared'
import type { MarketMessage, OrderTimelineEvent, StrategySignal } from '../types/contracts'

type Translate = (key: TranslationKey) => string

const LOCALE_STORAGE_KEY = 'cerberus.locale'

type EmptyStateKind =
  | 'generic'
  | 'time'
  | 'request-id'
  | 'order-id'
  | 'client-order-id'
  | 'execution-id'
  | 'bid'
  | 'ask'
  | 'mid'
  | 'spread'
  | 'latency'
  | 'quote-time'
  | 'feedback-time'

const EMPTY_STATE_LABELS: Record<'zh-CN' | 'en-US', Record<EmptyStateKind, string>> = {
  'zh-CN': {
    generic: '—',
    time: '—',
    'request-id': '—',
    'order-id': '—',
    'client-order-id': '—',
    'execution-id': '—',
    bid: '买盘待形成',
    ask: '卖盘待形成',
    mid: '等待双边形成',
    spread: '等待双边形成',
    latency: '—',
    'quote-time': '—',
    'feedback-time': '—',
  },
  'en-US': {
    generic: '—',
    time: '—',
    'request-id': '—',
    'order-id': '—',
    'client-order-id': '—',
    'execution-id': '—',
    bid: 'Bid pending',
    ask: 'Ask pending',
    mid: 'Waiting for both sides',
    spread: 'Waiting for both sides',
    latency: '—',
    'quote-time': '—',
    'feedback-time': '—',
  },
}

function resolveUiLocale(): 'zh-CN' | 'en-US' {
  if (typeof window !== 'undefined') {
    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY)
    if (stored === 'zh-CN' || stored === 'en-US') {
      return stored
    }
  }
  if (typeof navigator !== 'undefined' && navigator.language.toLowerCase().startsWith('zh')) {
    return 'zh-CN'
  }
  return 'en-US'
}

export function formatEmptyStateLabel(kind: EmptyStateKind = 'generic'): string {
  return EMPTY_STATE_LABELS[resolveUiLocale()][kind]
}

export type WorkspaceSummaryModel = {
  id: WorkspaceId
  titleKey: TranslationKey
  descriptionKey: TranslationKey
  indexLabel: string
  accent: 'teal' | 'cyan' | 'amber'
  groupId: 'command' | 'market' | 'decision' | 'execution' | 'runtime'
}

export type WorkspaceRailGroupModel = {
  id: WorkspaceSummaryModel['groupId']
  titleKey: TranslationKey
  descriptionKey: TranslationKey
  items: WorkspaceSummaryModel[]
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
  visualPriority?: 'primary' | 'secondary'
}

export type WorkspaceSpotlightModel = {
  summary: string
  hint?: string
  chips: string[]
  metrics: WorkspaceSpotlightMetricModel[]
  accent?: 'teal' | 'cyan' | 'amber'
  postureLabel?: string
}

export type WorkspaceOperatorDeckItemModel = {
  id: string
  label: string
  value: string
  tone?: 'default' | 'muted' | 'accent' | 'positive' | 'negative'
}

export type WorkspaceOperatorDeckSectionModel = {
  id: string
  title: string
  summary?: string
  items: WorkspaceOperatorDeckItemModel[]
  accent?: 'teal' | 'cyan' | 'amber'
  postureLabel?: string
  visualPriority?: 'hero' | 'default'
}

export type WorkspaceContextBandModel = {
  eyebrow: string
  title: string
  hint: string
  items: WorkspaceOperatorDeckItemModel[]
  accent?: 'teal' | 'cyan' | 'amber'
}

export type CoreFlowStepCardModel = {
  id: CoreFlowStepId
  title: string
  indexLabel: string
  updatedAt: string
  state: CoreFlowStepState
  stateLabel: string
  reason: string
  requestId?: string
}

export type CoreFlowPanelModel = {
  summary: string
  hint: string
  steps: CoreFlowStepCardModel[]
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
    indexLabel: '01',
    accent: 'cyan',
    groupId: 'command',
  },
  {
    id: 'market',
    titleKey: 'workspace.market.title',
    descriptionKey: 'workspace.market.description',
    indexLabel: '02',
    accent: 'cyan',
    groupId: 'market',
  },
  {
    id: 'book',
    titleKey: 'workspace.book.title',
    descriptionKey: 'workspace.book.description',
    indexLabel: '03',
    accent: 'cyan',
    groupId: 'market',
  },
  {
    id: 'strategy',
    titleKey: 'workspace.strategy.title',
    descriptionKey: 'workspace.strategy.description',
    indexLabel: '04',
    accent: 'teal',
    groupId: 'decision',
  },
  {
    id: 'execution',
    titleKey: 'workspace.execution.title',
    descriptionKey: 'workspace.execution.description',
    indexLabel: '05',
    accent: 'amber',
    groupId: 'execution',
  },
  {
    id: 'inference',
    titleKey: 'workspace.inference.title',
    descriptionKey: 'workspace.inference.description',
    indexLabel: '06',
    accent: 'teal',
    groupId: 'decision',
  },
  {
    id: 'health',
    titleKey: 'workspace.health.title',
    descriptionKey: 'workspace.health.description',
    indexLabel: '07',
    accent: 'teal',
    groupId: 'runtime',
  },
]

export const WORKSPACE_GROUPS: WorkspaceRailGroupModel[] = [
  {
    id: 'command',
    titleKey: 'shell.group.command',
    descriptionKey: 'shell.group.commandDescription',
    items: WORKSPACE_MODELS.filter((item) => item.groupId === 'command'),
  },
  {
    id: 'market',
    titleKey: 'shell.group.market',
    descriptionKey: 'shell.group.marketDescription',
    items: WORKSPACE_MODELS.filter((item) => item.groupId === 'market'),
  },
  {
    id: 'decision',
    titleKey: 'shell.group.decision',
    descriptionKey: 'shell.group.decisionDescription',
    items: WORKSPACE_MODELS.filter((item) => item.groupId === 'decision'),
  },
  {
    id: 'execution',
    titleKey: 'shell.group.execution',
    descriptionKey: 'shell.group.executionDescription',
    items: WORKSPACE_MODELS.filter((item) => item.groupId === 'execution'),
  },
  {
    id: 'runtime',
    titleKey: 'shell.group.runtime',
    descriptionKey: 'shell.group.runtimeDescription',
    items: WORKSPACE_MODELS.filter((item) => item.groupId === 'runtime'),
  },
]

export const WORKSPACE_INDEX_BY_ID = Object.fromEntries(
  WORKSPACE_MODELS.map((item, index) => [item.id, index]),
) as Record<WorkspaceId, number>

export const WORKSPACE_MODEL_BY_ID = Object.fromEntries(
  WORKSPACE_MODELS.map((item) => [item.id, item]),
) as Record<WorkspaceId, WorkspaceSummaryModel>

export function getWorkspaceAccent(workspace: WorkspaceId): WorkspaceSummaryModel['accent'] {
  return WORKSPACE_MODEL_BY_ID[workspace].accent
}

const CORE_FLOW_STEP_ORDER: CoreFlowStepId[] = ['bootstrap', 'market', 'precheck', 'submit', 'feedback', 'cancel']

const CORE_FLOW_STEP_LABEL_MAP: Record<CoreFlowStepId, TranslationKey> = {
  bootstrap: 'flow.step.bootstrap',
  market: 'flow.step.market',
  precheck: 'flow.step.precheck',
  submit: 'flow.step.submit',
  feedback: 'flow.step.feedback',
  cancel: 'flow.step.cancel',
}

const CORE_FLOW_STATE_LABEL_MAP: Record<CoreFlowStepState, TranslationKey> = {
  idle: 'health.state.idle',
  active: 'health.state.loading',
  success: 'health.state.ready',
  degraded: 'health.state.degraded',
  error: 'health.state.error',
}

export function parseDateTimeValue(value?: number | string | null): number | undefined {
  if (value === undefined || value === null || value === '') {
    return undefined
  }
  if (typeof value === 'number') {
    return Number.isNaN(value) ? undefined : value
  }
  const trimmed = value.trim()
  if (!trimmed) {
    return undefined
  }
  const numeric = Number(trimmed)
  if (Number.isFinite(numeric) && /^\d+(\.\d+)?$/.test(trimmed)) {
    return numeric
  }
  const parsed = Date.parse(trimmed)
  return Number.isNaN(parsed) ? undefined : parsed
}

export function formatDateTimeLabel(
  value?: number | string | null,
  fallback = formatEmptyStateLabel('time'),
): string {
  if (value === undefined || value === null || value === '') {
    return fallback
  }
  const parsed = parseDateTimeValue(value)
  if (parsed === undefined) {
    return typeof value === 'string' ? value : fallback
  }
  return new Date(parsed).toLocaleString()
}

export function formatRequestLabel(value?: string | null, fallback = formatEmptyStateLabel('generic')): string {
  return value?.trim() ? value : fallback
}

export function formatNumber(value?: number | null, digits = 2, fallback = formatEmptyStateLabel('generic')): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return fallback
  }
  return value.toFixed(digits)
}

export function formatPrice(value?: string | null, fallback = formatEmptyStateLabel('generic')): string {
  return value?.trim() ? value : fallback
}

export function formatDerivedPrice(
  value?: number | null,
  digits = 6,
  fallback = formatEmptyStateLabel('generic'),
): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return fallback
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
      updatedAt: formatDateTimeLabel(value.last_update_ms),
      requestId: value.request_id,
      reason: value.reason,
    }),
  )
}

export function buildExecutionRows(events: OrderTimelineEvent[], t: Translate): ExecutionFeedRowModel[] {
  return events.map((event) => ({
    id: event.id,
    title: `${event.event_type} · ${event.lifecycle_phase}`,
    subtitle: [
      formatRequestLabel(event.symbol),
      formatRequestLabel(event.account_id),
      formatRequestLabel(event.client_order_id ?? event.request_id, formatEmptyStateLabel('request-id')),
    ].join(' · '),
    rightTop: event.status ?? event.lifecycle_phase,
    rightBottom: `${t('execution.receivedAt')}: ${formatDateTimeLabel(event.received_at)}`,
  }))
}

export function summarizeLatestFeedback(event: OrderTimelineEvent | undefined, heartbeat: string | undefined, t: Translate) {
  if (!event) {
    return heartbeat ?? t('common.heartbeat')
  }
  return `${event.event_type} · ${formatRequestLabel(event.symbol)} · ${formatRequestLabel(event.status)}`
}

export function summarizeLatestEventAt(event: OrderTimelineEvent | undefined) {
  return formatDateTimeLabel(event?.event_time ?? event?.received_at, formatEmptyStateLabel('feedback-time'))
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

export function buildCoreFlowPanelModel(flow: CoreFlowMap, t: Translate): CoreFlowPanelModel {
  let readyCount = 0
  let loadingCount = 0
  let attentionCount = 0
  let latestUpdateMs: number | null = null

  const steps = CORE_FLOW_STEP_ORDER.map((step, index) => {
    const item = flow[step]

    if (item.state === 'success') {
      readyCount += 1
    } else if (item.state === 'active') {
      loadingCount += 1
    } else if (item.state === 'degraded' || item.state === 'error') {
      attentionCount += 1
    }

    if (typeof item.last_update_ms === 'number' && Number.isFinite(item.last_update_ms)) {
      latestUpdateMs = latestUpdateMs === null ? item.last_update_ms : Math.max(latestUpdateMs, item.last_update_ms)
    }

    return {
      id: step,
      title: t(CORE_FLOW_STEP_LABEL_MAP[step]),
      indexLabel: `${index + 1}.`,
      updatedAt: formatDateTimeLabel(item.last_update_ms),
      state: item.state,
      stateLabel: t(CORE_FLOW_STATE_LABEL_MAP[item.state]),
      reason: item.reason?.trim() ? item.reason : t('common.na'),
      requestId: item.request_id?.trim() ? item.request_id : undefined,
    }
  })

  const summaryParts = [
    `${readyCount} ${t('common.ready')}`,
    `${loadingCount} ${t('health.state.loading')}`,
  ]
  if (attentionCount > 0) {
    summaryParts.push(`${attentionCount} ${t('workspace.overview.attention')}`)
  }

  return {
    summary: summaryParts.join(' · '),
    hint: `${t('common.updatedAt')}: ${formatDateTimeLabel(latestUpdateMs)}`,
    steps,
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
    bestBidValue: formatPrice(displayQuote?.bid_price, formatEmptyStateLabel('bid')),
    bestAskValue: formatPrice(displayQuote?.ask_price, formatEmptyStateLabel('ask')),
    midPriceValue: formatDerivedPrice(midPrice, 6, formatEmptyStateLabel('mid')),
    spreadValue: formatDerivedPrice(spread, 6, formatEmptyStateLabel('spread')),
    signalValue: strategySignal?.signal ?? 'HOLD',
    confidenceValue: formatConfidence(strategySignal?.confidence),
    feedbackValue: latestEvent
      ? `${latestEvent.event_type} · ${formatRequestLabel(latestEvent.symbol)} · ${formatRequestLabel(latestEvent.status)}`
      : heartbeat,
    feedbackAtValue: summarizeLatestEventAt(latestEvent),
    quoteUpdatedAtValue: formatDateTimeLabel(displayQuote?.event_time, formatEmptyStateLabel('quote-time')),
  }
}
