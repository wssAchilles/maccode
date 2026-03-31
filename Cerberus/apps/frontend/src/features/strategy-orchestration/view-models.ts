import type { TranslationKey } from '../../i18n/messages'
import type {
  BinanceRule,
  OrderTimelineEvent,
  PersistenceStatus,
  StrategyDecisionContribution,
  StrategyRegistrySummary,
  StrategySignal,
  TradingPolicy,
  UIState,
} from '../../types/contracts'
import { formatConfidence } from '../../view-models/workbench'
import { buildExecutionOrderReadModels } from '../execution/read-models'

type Translate = (key: TranslationKey) => string

export type StrategyDecisionRowModel = {
  id: string
  label: string
  engine: string
  signal: string
  confidence: string
  weight: string
  priority: string
  source: string
  role: string
  reason?: string
  active: boolean
  tone?: 'default' | 'positive' | 'negative' | 'accent'
}

export type StrategyDecisionMatrixModel = {
  summary: string
  hint: string
  signalId?: string
  items: StrategyDecisionRowModel[]
  emptyTitle?: string
  emptyHint?: string
}

export type StrategyPortfolioPanelModel = {
  summary: string
  biasLabel: string
  gateLabel: string
  gateTone: 'default' | 'muted' | 'accent'
  symbolChips: { id: string; label: string; active: boolean }[]
  items: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
  emptyTitle?: string
  emptyHint?: string
}

export type StrategyRegistryRowModel = {
  id: string
  label: string
  engine: string
  stateLabel: string
  stateTone: 'default' | 'muted' | 'accent'
  items: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
}

export type StrategyRegistryPanelModel = {
  summary: string
  policyLabel: string
  downgradeLabel: string
  stateSummary?: string
  rows: StrategyRegistryRowModel[]
  emptyTitle?: string
  emptyHint?: string
}

export type ExecutionLifecycleStageModel = {
  id: string
  label: string
  detail: string
  state: 'idle' | 'loading' | 'ready' | 'degraded' | 'error'
}

export type ExecutionLifecyclePanelModel = {
  state: 'idle' | 'loading' | 'ready' | 'degraded' | 'error'
  stateLabel: string
  summary: string
  reason?: string
  stages: ExecutionLifecycleStageModel[]
  items: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return '—'
  }
  const parsed = Date.parse(value)
  if (Number.isNaN(parsed)) {
    return value
  }
  return new Date(parsed).toLocaleString()
}

function formatPercent(value?: number | null): string {
  if (value === undefined || value === null || !Number.isFinite(value)) {
    return '—'
  }
  return `${(value * 100).toFixed(1)}%`
}

function formatInteger(value?: number | null): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '—'
  }
  return String(value)
}

function formatFloat(value?: number | null, digits = 3): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '—'
  }
  return value.toFixed(digits)
}

function decisionTone(signal: string): StrategyDecisionRowModel['tone'] {
  if (signal === 'BUY') {
    return 'positive'
  }
  if (signal === 'SELL') {
    return 'negative'
  }
  if (signal === 'HOLD') {
    return 'accent'
  }
  return 'default'
}

function biasLabel(t: Translate, bias?: string): string {
  if (!bias) {
    return t('common.na')
  }
  const key = `workspace.strategy.bias.${bias}` as TranslationKey
  return t(key)
}

function sourceLabel(t: Translate, source?: string): string {
  if (!source) {
    return t('common.na')
  }
  const key = `workspace.strategy.source.${source}` as TranslationKey
  return t(key)
}

function roleLabel(t: Translate, role?: string): string {
  if (!role) {
    return t('common.na')
  }
  const key = `workspace.strategy.role.${role}` as TranslationKey
  return t(key)
}

function consensusLabel(t: Translate, value?: string): string {
  if (!value) {
    return t('common.na')
  }
  const key = `workspace.strategy.consensus.${value}` as TranslationKey
  return t(key)
}

function executionGateLabel(t: Translate, value?: string): string {
  if (!value) {
    return t('common.na')
  }
  const key = `workspace.strategy.gate.${value}` as TranslationKey
  return t(key)
}

function conflictPolicyLabel(t: Translate, value?: string): string {
  if (!value) {
    return t('common.na')
  }
  const key = `workspace.strategy.conflict.${value}` as TranslationKey
  return t(key)
}

function downgradePolicyLabel(t: Translate, value?: string): string {
  if (!value) {
    return t('common.na')
  }
  const key = `workspace.strategy.downgrade.${value}` as TranslationKey
  return t(key)
}

function lifecycleStatusLabel(t: Translate, value?: string, eventType?: string): string {
  const normalized = `${value ?? ''}`.trim().toLowerCase()
  if (normalized === 'filled') {
    return t('workspace.execution.lifecycleStatus.filled')
  }
  if (normalized === 'partial_fill' || normalized === 'partially_filled') {
    return t('workspace.execution.lifecycleStatus.partialFill')
  }
  if (normalized === 'fill') {
    return t('workspace.execution.lifecycleStatus.filled')
  }
  if (normalized === 'submitted' || normalized === 'accepted') {
    return t('workspace.execution.lifecycleStatus.submitted')
  }
  if (normalized === 'submit') {
    return t('workspace.execution.lifecycleStatus.submitted')
  }
  if (normalized === 'rejected') {
    return t('workspace.execution.lifecycleStatus.rejected')
  }
  if (normalized === 'canceled' || normalized === 'cancelled') {
    return t('workspace.execution.lifecycleStatus.canceled')
  }
  if (normalized === 'cancel_requested') {
    return t('workspace.execution.lifecycleStatus.cancelRequested')
  }
  if ((eventType ?? '').includes('execution.filled')) {
    return t('workspace.execution.lifecycleStatus.filled')
  }
  return t('health.state.idle')
}

function lifecycleStateFromStatus(
  status?: string,
  eventType?: string,
): ExecutionLifecycleStageModel['state'] {
  const normalized = `${status ?? ''}`.trim().toLowerCase()
  if (normalized === 'filled' || normalized === 'fill' || normalized === 'submitted' || normalized === 'submit' || normalized === 'accepted') {
    return 'ready'
  }
  if (normalized === 'partial_fill' || normalized === 'partially_filled' || normalized === 'cancel_requested' || normalized === 'canceled' || normalized === 'cancelled') {
    return 'degraded'
  }
  if (normalized === 'rejected') {
    return 'error'
  }
  if ((eventType ?? '').includes('execution.filled')) {
    return 'ready'
  }
  return 'idle'
}

function summarizeCoverage(selectedSymbol: string | undefined, coverage: string[]): string {
  if (coverage.length === 0) {
    return '—'
  }
  if (!selectedSymbol) {
    return coverage.join(' · ')
  }
  if (coverage.includes(selectedSymbol)) {
    return `${selectedSymbol} · ${coverage.length}/${coverage.length}`
  }
  return coverage.join(' · ')
}

function lifecycleStateLabel(
  t: Translate,
  state: ExecutionLifecyclePanelModel['state'],
): string {
  if (state === 'loading') {
    return t('health.state.loading')
  }
  if (state === 'ready') {
    return t('health.state.ready')
  }
  if (state === 'degraded') {
    return t('health.state.degraded')
  }
  if (state === 'error') {
    return t('health.state.error')
  }
  return t('health.state.idle')
}

export function buildStrategyDecisionMatrixModel({
  t,
  signal,
}: {
  t: Translate
  signal?: StrategySignal
}): StrategyDecisionMatrixModel {
  const basket = signal?.strategy_basket ?? []
  if (basket.length === 0) {
    return {
      summary: t('workspace.strategy.noDecisions'),
      hint: t('workspace.strategy.noDecisionsHint'),
      items: [],
      emptyTitle: t('workspace.strategy.noDecisions'),
      emptyHint: t('workspace.strategy.noDecisionsHint'),
    }
  }

  const rows = [...basket]
    .sort((left, right) => left.priority - right.priority)
    .map((item: StrategyDecisionContribution) => ({
      id: `${item.strategy_id}-${item.engine}`,
      label: item.label,
      engine: item.engine,
      signal: item.signal,
      confidence: formatConfidence(item.confidence),
      weight: `${(item.weight * 100).toFixed(0)}%`,
      priority: String(item.priority),
      source: sourceLabel(t, item.source),
      role: roleLabel(t, item.role),
      reason: item.reason ?? undefined,
      active: item.active,
      tone: decisionTone(item.signal),
    }))

  return {
    summary: `${signal?.signal ?? 'HOLD'} · ${sourceLabel(t, signal?.decision_source)}`,
    hint: signal?.engine ?? t('common.na'),
    signalId: signal?.signal_id,
    items: rows,
  }
}

export function buildStrategyPortfolioPanelModel({
  t,
  signal,
  selectedSymbol,
}: {
  t: Translate
  signal?: StrategySignal
  selectedSymbol?: string
}): StrategyPortfolioPanelModel {
  const portfolio = signal?.portfolio
  if (!portfolio) {
    return {
      summary: t('workspace.strategy.portfolioEmpty'),
      biasLabel: t('common.na'),
      gateLabel: t('common.na'),
      gateTone: 'muted',
      symbolChips: [],
      items: [],
      emptyTitle: t('workspace.strategy.portfolioEmpty'),
      emptyHint: t('workspace.strategy.noDecisionsHint'),
    }
  }

  const gateTone =
    portfolio.execution_gate === 'ready'
      ? 'accent'
      : portfolio.execution_gate === 'hold'
        ? 'muted'
        : 'default'

  return {
    summary: `${portfolio.dominant_signal} · ${sourceLabel(t, portfolio.final_source)}`,
    biasLabel: biasLabel(t, portfolio.signal_bias),
    gateLabel: executionGateLabel(t, portfolio.execution_gate),
    gateTone,
    symbolChips: portfolio.tracked_symbols.map((symbol) => ({
      id: symbol,
      label: symbol,
      active: symbol === selectedSymbol,
    })),
    items: [
      {
        id: 'finalSignal',
        label: t('workspace.strategy.finalSignal'),
        value: portfolio.final_signal,
        tone: decisionTone(portfolio.final_signal) === 'accent' ? 'accent' : 'default',
      },
      {
        id: 'agreementRate',
        label: t('workspace.strategy.agreementRate'),
        value: formatPercent(portfolio.agreement_ratio),
      },
      {
        id: 'coverage',
        label: t('workspace.strategy.coverage'),
        value: formatInteger(portfolio.tracked_symbols.length),
      },
      {
        id: 'activeStrategies',
        label: t('workspace.strategy.activeStrategies'),
        value: formatInteger(portfolio.active_strategy_count),
      },
      {
        id: 'weightedScore',
        label: t('workspace.strategy.weightedScore'),
        value: formatFloat(portfolio.weighted_score, 3),
        tone: 'accent',
      },
      {
        id: 'consensusLevel',
        label: t('workspace.strategy.consensusTitle'),
        value: consensusLabel(t, portfolio.consensus_level),
      },
      {
        id: 'executionGate',
        label: t('workspace.strategy.executionGate'),
        value: executionGateLabel(t, portfolio.execution_gate),
        tone: gateTone,
      },
      {
        id: 'leadStrategy',
        label: t('workspace.strategy.leadStrategy'),
        value: portfolio.lead_strategy_label ?? t('common.na'),
      },
      {
        id: 'latestPrice',
        label: t('workspace.strategy.latestPrice'),
        value: formatFloat(portfolio.latest_price, 2),
      },
      {
        id: 'updatedAt',
        label: t('workspace.strategy.updatedAt'),
        value: formatDateTime(portfolio.updated_at),
      },
    ],
  }
}

export function buildStrategyRegistryPanelModel({
  t,
  signal,
  selectedSymbol,
}: {
  t: Translate
  signal?: StrategySignal
  selectedSymbol?: string
}): StrategyRegistryPanelModel {
  const registry = signal?.strategy_registry
  if (!registry || registry.entries.length === 0) {
    return {
      summary: t('workspace.strategy.registryEmpty'),
      policyLabel: t('common.na'),
      downgradeLabel: t('common.na'),
      stateSummary: t('common.na'),
      rows: [],
      emptyTitle: t('workspace.strategy.registryEmpty'),
      emptyHint: t('workspace.strategy.noDecisionsHint'),
    }
  }

  const rows: StrategyRegistryRowModel[] = [...registry.entries]
    .sort((left, right) => left.priority - right.priority)
    .map((entry) => {
      const stateTone: StrategyRegistryRowModel['stateTone'] = entry.enabled ? 'accent' : 'muted'
      return {
        id: `${entry.strategy_id}-${entry.engine}`,
        label: entry.label,
        engine: entry.engine,
        stateLabel: entry.enabled ? t('common.ready') : t('common.disabled'),
        stateTone,
        items: [
          {
            id: 'runtimeState',
            label: t('workspace.strategy.runtimeState'),
            value: entry.metadata.state_restored
              ? t('workspace.strategy.runtimeStateRestored')
              : entry.enabled
                ? t('common.ready')
                : t('common.disabled'),
            tone: entry.metadata.state_restored ? 'accent' : 'default',
          },
          {
            id: 'priority',
            label: t('workspace.strategy.priority'),
            value: String(entry.priority),
          },
          {
            id: 'configuredWeight',
            label: t('workspace.strategy.configuredWeight'),
            value: formatPercent(entry.configured_weight),
          },
          {
            id: 'effectiveWeight',
            label: t('workspace.strategy.effectiveWeight'),
            value: formatPercent(entry.effective_weight),
            tone: 'accent',
          },
          {
            id: 'coverage',
            label: t('workspace.strategy.symbolCoverage'),
            value: summarizeCoverage(selectedSymbol, entry.symbol_coverage),
          },
          {
            id: 'role',
            label: t('workspace.strategy.role'),
            value: roleLabel(t, entry.role),
          },
          {
            id: 'source',
            label: t('workspace.strategy.lifecycleSource'),
            value: sourceLabel(t, entry.source),
          },
        ],
      }
    })

  return {
    summary: `${registry.entries.length} ${t('workspace.strategy.registrySummarySuffix')} · ${registry.symbol}`,
    policyLabel: conflictPolicyLabel(t, registry.conflict_policy),
    downgradeLabel: downgradePolicyLabel(t, registry.downgrade_policy),
    stateSummary: `${registry.entries.some((entry) => entry.metadata.state_restored) ? t('workspace.strategy.runtimeStateSummaryRestored') : t('workspace.strategy.runtimeStateSummaryLive')} · ${registry.tracked_symbols.length} ${t('workspace.strategy.trackedSymbolsSuffix')}`,
    rows,
  }
}

export function buildExecutionLifecyclePanelModel({
  t,
  signal,
  persistenceStatus,
  orderEvents,
  selectedSymbol,
  latestEventSummary,
  heartbeat,
  tradingPolicy,
  binanceRule,
  domainStatus,
}: {
  t: Translate
  signal?: StrategySignal
  persistenceStatus?: PersistenceStatus
  orderEvents?: OrderTimelineEvent[]
  selectedSymbol?: string
  latestEventSummary: string
  heartbeat?: string
  tradingPolicy?: TradingPolicy
  binanceRule?: BinanceRule
  domainStatus: UIState
}): ExecutionLifecyclePanelModel {
  const state = domainStatus.state
  const stateLabel = lifecycleStateLabel(t, state)
  const matchingStats = persistenceStatus?.matching?.stats
  const filteredEvents = (orderEvents ?? []).filter((item) =>
    selectedSymbol ? item.symbol === selectedSymbol : true,
  )
  const orderModels = buildExecutionOrderReadModels(filteredEvents, selectedSymbol)
  const latestLifecycleEvent = orderModels[0]
  const partialFillCount = orderModels.filter((item) => item.latestPhase === 'partial_fill').length
  const filledCount = orderModels.filter((item) => item.latestPhase === 'fill').length
  const canceledCount = orderModels.filter((item) => item.latestPhase === 'canceled').length
  const rejectedCount = orderModels.filter((item) => item.latestPhase === 'rejected').length
  const summary = latestEventSummary === t('common.heartbeat') && heartbeat
    ? heartbeat
    : latestEventSummary
  const dispatchState = signal?.dispatch_state ?? 'idle'
  const portfolioGate = signal?.portfolio?.execution_gate
  const stages: ExecutionLifecycleStageModel[] = [
    {
      id: 'dispatch',
      label: t('workspace.execution.lifecycleStageDispatch'),
      detail: dispatchState,
      state:
        dispatchState === 'accepted'
          ? 'ready'
          : dispatchState === 'duplicate'
            ? 'degraded'
            : dispatchState === 'rejected'
              ? 'error'
              : 'idle',
    },
    {
      id: 'policy',
      label: t('workspace.execution.lifecycleStagePolicy'),
      detail:
        portfolioGate
          ? executionGateLabel(t, portfolioGate)
          : tradingPolicy?.enforced
            ? t('common.ready')
            : t('common.disabled'),
      state:
        portfolioGate === 'ready'
          ? 'ready'
          : portfolioGate === 'review'
            ? 'degraded'
            : portfolioGate === 'hold'
              ? 'idle'
              : tradingPolicy?.enforced
                ? 'ready'
                : 'degraded',
    },
    {
      id: 'venue',
      label: t('workspace.execution.lifecycleStageVenue'),
      detail: binanceRule ? t('common.ready') : t('workspace.execution.lifecycleWaitingRule'),
      state: binanceRule ? 'ready' : 'loading',
    },
    {
      id: 'execution',
      label: t('workspace.execution.lifecycleStageExecution'),
      detail: lifecycleStatusLabel(t, latestLifecycleEvent?.latestStatus, latestLifecycleEvent?.latestPhase),
      state: lifecycleStateFromStatus(latestLifecycleEvent?.latestStatus, latestLifecycleEvent?.latestPhase),
    },
  ]

  return {
    state,
    stateLabel,
    summary,
    reason: domainStatus.reason,
    stages,
    items: [
      {
        id: 'dispatchState',
        label: t('workspace.execution.lifecycleDispatch'),
        value: signal?.dispatch_state ?? t('common.na'),
      },
      {
        id: 'decisionSource',
        label: t('workspace.execution.lifecycleSource'),
        value: sourceLabel(t, signal?.decision_source),
      },
      {
        id: 'policy',
        label: t('workspace.execution.lifecyclePolicy'),
        value:
          portfolioGate
            ? executionGateLabel(t, portfolioGate)
            : tradingPolicy?.enforced
              ? t('common.ready')
              : t('common.disabled'),
        tone: portfolioGate === 'ready' || tradingPolicy?.enforced ? 'accent' : 'muted',
      },
      {
        id: 'ruleReady',
        label: t('workspace.execution.lifecycleVenueRule'),
        value: binanceRule ? t('common.ready') : t('workspace.execution.lifecycleWaitingRule'),
      },
      {
        id: 'latestLifecycle',
        label: t('workspace.execution.lifecycleLatest'),
        value: lifecycleStatusLabel(t, latestLifecycleEvent?.latestStatus, latestLifecycleEvent?.latestPhase),
      },
      {
        id: 'latestRequestId',
        label: t('workspace.execution.lifecycleRequestId'),
        value: latestLifecycleEvent?.requestId ?? t('common.na'),
      },
      {
        id: 'latestOrderId',
        label: t('workspace.execution.lifecycleOrderId'),
        value: latestLifecycleEvent?.orderId ?? t('common.na'),
      },
      {
        id: 'latestExecutionId',
        label: t('workspace.execution.lifecycleExecutionId'),
        value: latestLifecycleEvent?.executionIds[0] ?? t('common.na'),
      },
      {
        id: 'latestClientOrderId',
        label: t('workspace.execution.lifecycleClientOrderId'),
        value: latestLifecycleEvent?.clientOrderId ?? t('common.na'),
      },
      {
        id: 'forwardedExecutions',
        label: t('workspace.execution.lifecycleForwarded'),
        value: formatInteger(persistenceStatus?.worker.forwarded_executions),
      },
      {
        id: 'partialFills',
        label: t('workspace.execution.lifecyclePartialFills'),
        value: formatInteger(partialFillCount),
      },
      {
        id: 'filledCount',
        label: t('workspace.execution.lifecycleFilledCount'),
        value: formatInteger(filledCount),
      },
      {
        id: 'canceledCount',
        label: t('workspace.execution.lifecycleCanceledCount'),
        value: formatInteger(canceledCount),
      },
      {
        id: 'lastExecutionId',
        label: t('workspace.execution.lifecycleLastExecutionId'),
        value: formatInteger(persistenceStatus?.worker.last_execution_id),
      },
      {
        id: 'liveOrders',
        label: t('workspace.execution.lifecycleLiveOrders'),
        value: formatInteger(matchingStats?.live_orders),
      },
      {
        id: 'rejectedOrders',
        label: t('workspace.execution.lifecycleRejectedOrders'),
        value: formatInteger(rejectedCount || matchingStats?.rejected_orders),
      },
    ],
  }
}
