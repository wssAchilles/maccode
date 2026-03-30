import type { TranslationKey } from '../../i18n/messages'
import type {
  BinanceRule,
  PersistenceStatus,
  StrategyDecisionContribution,
  StrategySignal,
  TradingPolicy,
  UIState,
} from '../../types/contracts'
import { formatConfidence } from '../../view-models/workbench'

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

export function buildExecutionLifecyclePanelModel({
  t,
  signal,
  persistenceStatus,
  latestEventSummary,
  heartbeat,
  tradingPolicy,
  binanceRule,
  domainStatus,
}: {
  t: Translate
  signal?: StrategySignal
  persistenceStatus?: PersistenceStatus
  latestEventSummary: string
  heartbeat?: string
  tradingPolicy?: TradingPolicy
  binanceRule?: BinanceRule
  domainStatus: UIState
}): ExecutionLifecyclePanelModel {
  const state = domainStatus.state
  const stateLabel = lifecycleStateLabel(t, state)
  const matchingStats = persistenceStatus?.matching?.stats
  const summary = latestEventSummary === t('common.heartbeat') && heartbeat
    ? heartbeat
    : latestEventSummary
  const dispatchState = signal?.dispatch_state ?? 'idle'
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
      detail: tradingPolicy?.enforced ? t('common.ready') : t('common.disabled'),
      state: tradingPolicy?.enforced ? 'ready' : 'degraded',
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
      detail:
        (matchingStats?.rejected_orders ?? 0) > 0
          ? t('health.state.degraded')
          : (matchingStats?.live_orders ?? 0) > 0 || (persistenceStatus?.worker.forwarded_executions ?? 0) > 0
            ? t('health.state.ready')
            : t('health.state.idle'),
      state:
        (matchingStats?.rejected_orders ?? 0) > 0
          ? 'degraded'
          : (matchingStats?.live_orders ?? 0) > 0 || (persistenceStatus?.worker.forwarded_executions ?? 0) > 0
            ? 'ready'
            : 'idle',
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
        value: tradingPolicy?.enforced ? t('common.ready') : t('common.disabled'),
        tone: tradingPolicy?.enforced ? 'accent' : 'muted',
      },
      {
        id: 'ruleReady',
        label: t('workspace.execution.lifecycleVenueRule'),
        value: binanceRule ? t('common.ready') : t('workspace.execution.lifecycleWaitingRule'),
      },
      {
        id: 'forwardedExecutions',
        label: t('workspace.execution.lifecycleForwarded'),
        value: formatInteger(persistenceStatus?.worker.forwarded_executions),
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
        value: formatInteger(matchingStats?.rejected_orders),
      },
    ],
  }
}
