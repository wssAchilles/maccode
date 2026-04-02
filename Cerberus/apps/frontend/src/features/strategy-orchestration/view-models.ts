import type { TranslationKey } from '../../i18n/messages'
import type {
  BinanceRule,
  PersistenceStatus,
  StrategyDecisionContribution,
  StrategyOrchestrationControlResult,
  StrategyOrchestrationStatus,
  StrategyRegistrySummary,
  StrategySignal,
  TradingPolicy,
  UIState,
} from '../../types/contracts'
import { type WorkspaceContextBandModel, formatConfidence, formatDateTimeLabel } from '../../view-models/workbench'
import { type PreparedExecutionSelection } from '../execution/read-models'

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
  band?: WorkspaceContextBandModel
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
  impactLabel?: string
  detailHint?: string
  items: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
}

export type StrategyRegistryPanelModel = {
  summary: string
  policyLabel: string
  downgradeLabel: string
  stateSummary?: string
  band?: WorkspaceContextBandModel
  rows: StrategyRegistryRowModel[]
  emptyTitle?: string
  emptyHint?: string
}

export type StrategyOrchestrationAuditTimelineEntry = {
  id: string
  title: string
  message: string
  createdAt: string
  detail?: string
}

export type StrategyOrchestrationAuditTimelineModel = {
  summary: string
  band?: WorkspaceContextBandModel
  items: StrategyOrchestrationAuditTimelineEntry[]
  emptyTitle?: string
  emptyHint?: string
}

export type StrategyOrchestrationOperationsRowModel = {
  id: string
  label: string
  engine: string
  sourceLabel: string
  roleLabel: string
  stateLabel: string
  coverageLabel: string
  coverageScopeLabel: string
  conflictTargetsLabel: string
  downgradeActionLabel: string
  impactLabel: string
  lastUpdatedLabel: string
  lastActorLabel: string
  lastReasonLabel: string
}

export type StrategyOrchestrationOperationsModel = {
  summary: string
  policySummary: string
  rows: StrategyOrchestrationOperationsRowModel[]
  conflictOptions: { id: string; label: string }[]
  downgradeOptions: { id: string; label: string }[]
  pendingAction?: string
  statusMessage?: string
  statusTone?: 'default' | 'accent' | 'danger'
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
  summaryItems: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
  identifierItems: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
  telemetryItems: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
}

export type BuildStrategyContextBandParams = {
  t: Translate
  signal?: StrategySignal
  selectedSymbol?: string
  orchestrationStatus?: StrategyOrchestrationStatus
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

function coverageScopeLabel(t: Translate, value?: string): string {
  if (!value || value === 'all') {
    return t('workspace.strategy.coverageScopeAll')
  }
  if (value === 'selected') {
    return t('workspace.strategy.coverageScopeSelected')
  }
  return value
}

function impactLabel(
  t: Translate,
  {
    enabled,
    selectedSymbol,
    symbolCoverage,
    executionReady,
  }: {
    enabled: boolean
    selectedSymbol?: string
    symbolCoverage: string[]
    executionReady?: boolean
  },
): string {
  if (!enabled) {
    return t('workspace.strategy.impactDisabled')
  }
  if (selectedSymbol && symbolCoverage.length > 0 && !symbolCoverage.includes(selectedSymbol)) {
    return t('workspace.strategy.impactExcluded')
  }
  if (executionReady === false) {
    return t('workspace.strategy.impactReview')
  }
  return t('workspace.strategy.impactActive')
}

function changedFieldLabel(t: Translate, field: string): string {
  switch (field) {
    case 'enabled':
      return t('workspace.strategy.runtimeState')
    case 'priority':
      return t('workspace.strategy.priority')
    case 'observe_weight':
      return t('workspace.strategy.observeWeight')
    case 'primary_weight':
      return t('workspace.strategy.primaryWeight')
    case 'symbol_coverage':
      return t('workspace.strategy.symbolCoverage')
    case 'conflict_targets':
      return t('workspace.strategy.conflictTargets')
    case 'downgrade_action':
      return t('workspace.strategy.downgradeAction')
    case 'conflict_policy':
      return t('workspace.strategy.conflictPolicy')
    case 'downgrade_policy':
      return t('workspace.strategy.downgradePolicy')
    default:
      return field
  }
}

function toStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)) : []
}

function auditDiffLabel(t: Translate, field: string, metadata: Record<string, unknown>): string | undefined {
  const previous = metadata.previous
  const current = metadata.current
  if (!previous || !current || typeof previous !== 'object' || typeof current !== 'object') {
    return undefined
  }
  const previousValue = (previous as Record<string, unknown>)[field]
  const currentValue = (current as Record<string, unknown>)[field]
  const normalize = (value: unknown): string => {
    if (Array.isArray(value)) {
      return value.length > 0 ? value.map((item) => String(item)).join(' · ') : '—'
    }
    if (typeof value === 'boolean') {
      return value ? 'true' : 'false'
    }
    if (value === null || value === undefined || value === '') {
      return '—'
    }
    return String(value)
  }
  return `${changedFieldLabel(t, field)}: ${normalize(previousValue)} → ${normalize(currentValue)}`
}

function auditEventLabel(t: Translate, eventType?: string): string {
  if (!eventType) {
    return t('common.na')
  }
  const key = `workspace.strategy.auditEvent.${eventType}` as TranslationKey
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
    band: {
      eyebrow: t('workspace.strategy.matrixTitle'),
      title: `${signal?.signal ?? 'HOLD'} · ${sourceLabel(t, signal?.decision_source)}`,
      hint: signal?.engine ?? t('common.na'),
      accent: decisionTone(signal?.signal ?? 'HOLD') === 'positive'
        ? 'teal'
        : decisionTone(signal?.signal ?? 'HOLD') === 'negative'
          ? 'amber'
          : 'cyan',
      items: [
        {
          id: 'active',
          label: t('common.ready'),
          value: formatInteger(rows.filter((item) => item.active).length),
        },
        {
          id: 'rows',
          label: t('workspace.strategy.activeStrategies'),
          value: formatInteger(rows.length),
        },
        {
          id: 'signal-id',
          label: t('health.requestId'),
          value: signal?.signal_id ?? '—',
        },
        {
          id: 'lead-source',
          label: t('workspace.strategy.lifecycleSource'),
          value: sourceLabel(t, signal?.decision_source),
        },
      ],
    },
    items: rows,
  }
}

export function buildStrategyContextBandModel({
  t,
  signal,
  selectedSymbol,
  orchestrationStatus,
}: BuildStrategyContextBandParams): WorkspaceContextBandModel {
  const portfolio = signal?.portfolio
  const registry = signal?.strategy_registry
  const trackedSymbols = portfolio?.tracked_symbols ?? registry?.tracked_symbols ?? orchestrationStatus?.tracked_symbols ?? []
  const activeStrategies =
    portfolio?.active_strategy_count ??
    registry?.entries.filter((entry) => entry.enabled).length ??
    orchestrationStatus?.entries.filter((entry) => entry.enabled).length ??
    0
  const updatedAt =
    portfolio?.updated_at ??
    registry?.entries[0]?.last_updated_at ??
    orchestrationStatus?.audit[0]?.created_at
  const finalSignal = portfolio?.final_signal ?? signal?.signal ?? 'HOLD'
  const gateLabel = portfolio ? executionGateLabel(t, portfolio.execution_gate) : t('common.na')
  const consensus = portfolio ? consensusLabel(t, portfolio.consensus_level) : t('common.na')
  const source = sourceLabel(t, signal?.decision_source ?? portfolio?.final_source)

  return {
    eyebrow: t('workspace.strategy.portfolioTitle'),
    title: `${finalSignal} · ${source}`,
    hint: portfolio?.execution_gate_reason ?? t('workspace.strategy.description'),
    accent: gateLabel === t('workspace.strategy.gate.review') ? 'amber' : 'teal',
    items: [
      {
        id: 'symbol',
        label: 'Symbol',
        value: selectedSymbol ?? portfolio?.symbol ?? registry?.symbol ?? '—',
        tone: 'accent',
      },
      {
        id: 'final-signal',
        label: t('workspace.strategy.finalSignal'),
        value: finalSignal,
        tone: decisionTone(finalSignal) === 'accent' ? 'accent' : 'default',
      },
      {
        id: 'execution-gate',
        label: t('workspace.strategy.executionGate'),
        value: gateLabel,
      },
      {
        id: 'consensus',
        label: t('workspace.strategy.consensusTitle'),
        value: consensus,
      },
      {
        id: 'active-strategies',
        label: t('workspace.strategy.activeStrategies'),
        value: formatInteger(activeStrategies),
      },
      {
        id: 'tracked-symbols',
        label: t('workspace.strategy.coverage'),
        value: formatInteger(trackedSymbols.length),
      },
      {
        id: 'agreement-rate',
        label: t('workspace.strategy.agreementRate'),
        value: formatPercent(portfolio?.agreement_ratio),
      },
      {
        id: 'updated-at',
        label: t('common.updatedAt'),
        value: formatDateTimeLabel(updatedAt),
      },
    ],
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
        value: formatDateTimeLabel(portfolio.updated_at),
      },
    ],
  }
}

export function buildStrategyRegistryPanelModel({
  t,
  signal,
  selectedSymbol,
  orchestrationStatus,
}: {
  t: Translate
  signal?: StrategySignal
  selectedSymbol?: string
  orchestrationStatus?: StrategyOrchestrationStatus
}): StrategyRegistryPanelModel {
  const registry = signal?.strategy_registry
  const runtimeEntries = orchestrationStatus?.entries ?? registry?.entries ?? []
  if (runtimeEntries.length === 0) {
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

  const registryEntriesByStrategy = new Map(
    (registry?.entries ?? []).map((entry) => [entry.strategy_id, entry]),
  )

  const rows: StrategyRegistryRowModel[] = [...runtimeEntries]
    .sort((left, right) => left.priority - right.priority)
    .map((entry) => {
      const activeEntry = registryEntriesByStrategy.get(entry.strategy_id)
      const conflictTargets = Array.isArray(entry.conflict_targets)
        ? entry.conflict_targets
        : Array.isArray(entry.metadata.conflict_targets)
          ? (entry.metadata.conflict_targets as string[])
          : []
      const downgradeAction =
        entry.downgrade_action ||
        (typeof entry.metadata.downgrade_action === 'string' ? entry.metadata.downgrade_action : undefined)
      const stateTone: StrategyRegistryRowModel['stateTone'] = entry.enabled ? 'accent' : 'muted'
      const entryCoverage = entry.symbol_coverage
      const currentSelectedSymbol = selectedSymbol ?? registry?.symbol
      const registryImpact = impactLabel(t, {
        enabled: entry.enabled,
        selectedSymbol: currentSelectedSymbol,
        symbolCoverage: entryCoverage,
        executionReady: signal?.portfolio?.execution_ready,
      })
      const detailParts = [
        coverageScopeLabel(t, entry.coverage_scope),
        entry.last_actor ?? null,
        entry.last_reason ?? null,
      ].filter(Boolean)
      return {
        id: `${entry.strategy_id}-${entry.engine}-${entry.source}`,
        label: entry.label,
        engine: entry.engine,
        stateLabel: entry.enabled ? t('common.ready') : t('common.disabled'),
        stateTone,
        impactLabel: registryImpact,
        detailHint: detailParts.join(' · ') || undefined,
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
            value: formatPercent(
              activeEntry?.configured_weight ??
                ('observe_weight' in entry ? entry.observe_weight : entry.configured_weight),
            ),
          },
          {
            id: 'observeWeight',
            label: t('workspace.strategy.observeWeight'),
            value: formatPercent('observe_weight' in entry ? entry.observe_weight : entry.configured_weight),
          },
          {
            id: 'primaryWeight',
            label: t('workspace.strategy.primaryWeight'),
            value: formatPercent('primary_weight' in entry ? entry.primary_weight : entry.configured_weight),
          },
          {
            id: 'effectiveWeight',
            label: t('workspace.strategy.effectiveWeight'),
            value: formatPercent(activeEntry?.effective_weight ?? ('effective_weight' in entry ? (entry as { effective_weight?: number }).effective_weight : undefined)),
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
          {
            id: 'conflictTargets',
            label: t('workspace.strategy.conflictTargets'),
            value: conflictTargets.length > 0 ? conflictTargets.join(' · ') : t('common.na'),
          },
          {
            id: 'downgradeAction',
            label: t('workspace.strategy.downgradeAction'),
            value: downgradePolicyLabel(
              t,
              downgradeAction ?? orchestrationStatus?.downgrade_policy ?? registry?.downgrade_policy,
            ),
          },
        ],
      }
    })

  return {
    summary: `${runtimeEntries.length} ${t('workspace.strategy.registrySummarySuffix')} · ${orchestrationStatus?.tracked_symbols?.[0] ?? registry?.symbol ?? t('common.na')}`,
    policyLabel: conflictPolicyLabel(t, orchestrationStatus?.conflict_policy ?? registry?.conflict_policy),
    downgradeLabel: downgradePolicyLabel(t, orchestrationStatus?.downgrade_policy ?? registry?.downgrade_policy),
    stateSummary: `${orchestrationStatus?.state_restored ? t('workspace.strategy.runtimeStateSummaryRestored') : t('workspace.strategy.runtimeStateSummaryLive')} · ${(orchestrationStatus?.tracked_symbols ?? registry?.tracked_symbols ?? []).length} ${t('workspace.strategy.trackedSymbolsSuffix')}`,
    band: {
      eyebrow: t('workspace.strategy.registryTitle'),
      title: `${runtimeEntries.length} ${t('workspace.strategy.registrySummarySuffix')}`,
      hint: `${conflictPolicyLabel(t, orchestrationStatus?.conflict_policy ?? registry?.conflict_policy)} · ${downgradePolicyLabel(t, orchestrationStatus?.downgrade_policy ?? registry?.downgrade_policy)}`,
      accent: orchestrationStatus?.state_restored ? 'teal' : 'cyan',
      items: [
        {
          id: 'enabled',
          label: t('common.ready'),
          value: formatInteger(rows.filter((row) => row.stateTone === 'accent').length),
        },
        {
          id: 'tracked-symbols',
          label: t('workspace.strategy.coverage'),
          value: formatInteger((orchestrationStatus?.tracked_symbols ?? registry?.tracked_symbols ?? []).length),
        },
        {
          id: 'policy',
          label: t('workspace.strategy.conflictPolicy'),
          value: conflictPolicyLabel(t, orchestrationStatus?.conflict_policy ?? registry?.conflict_policy),
        },
        {
          id: 'downgrade',
          label: t('workspace.strategy.downgradePolicy'),
          value: downgradePolicyLabel(t, orchestrationStatus?.downgrade_policy ?? registry?.downgrade_policy),
        },
      ],
    },
    rows,
  }
}

export function buildStrategyOrchestrationAuditTimelineModel({
  t,
  orchestrationStatus,
}: {
  t: Translate
  orchestrationStatus?: StrategyOrchestrationStatus
}): StrategyOrchestrationAuditTimelineModel {
  const audit = orchestrationStatus?.audit ?? []
  if (audit.length === 0) {
    return {
      summary: t('workspace.strategy.auditTimelineEmpty'),
      items: [],
      emptyTitle: t('workspace.strategy.auditTimelineEmpty'),
      emptyHint: t('workspace.strategy.auditTimelineHint'),
    }
  }

  return {
    summary: `${audit.length} ${t('workspace.strategy.auditTimelineSummarySuffix')}`,
    band: {
      eyebrow: t('workspace.strategy.auditTimelineTitle'),
      title: `${audit.length} ${t('workspace.strategy.auditTimelineSummarySuffix')}`,
      hint: auditEventLabel(t, audit[0]?.event_type),
      accent: 'amber',
      items: [
        {
          id: 'events',
          label: t('workspace.strategy.auditTimelineSummarySuffix'),
          value: formatInteger(audit.length),
        },
        {
          id: 'latest-event',
          label: t('workspace.inference.recentAudit'),
          value: auditEventLabel(t, audit[0]?.event_type),
        },
        {
          id: 'latest-updated-at',
          label: t('common.updatedAt'),
          value: formatDateTimeLabel(audit[0]?.created_at),
        },
        {
          id: 'latest-actor',
          label: t('workspace.strategy.auditActor'),
          value: typeof audit[0]?.metadata.actor === 'string' ? audit[0].metadata.actor : '—',
        },
      ],
    },
    items: audit.map((item, index) => ({
      id: `${item.event_type}-${item.created_at}-${index}`,
      title: auditEventLabel(t, item.event_type),
      message: item.message,
      createdAt: formatDateTimeLabel(item.created_at),
      detail: (() => {
        const details: string[] = []
        if (typeof item.metadata.strategy_id === 'string') {
          details.push(`${t('workspace.strategy.auditStrategy')}: ${item.metadata.strategy_id}`)
        }
        if (typeof item.metadata.actor === 'string') {
          details.push(`${t('workspace.strategy.auditActor')}: ${item.metadata.actor}`)
        }
        if (typeof item.metadata.reason === 'string' && item.metadata.reason.trim()) {
          details.push(`${t('workspace.strategy.auditReason')}: ${item.metadata.reason}`)
        }
        const changedFields = toStringList(item.metadata.changed_fields)
        if (changedFields.length > 0) {
          details.push(
            `${t('workspace.strategy.auditChangedFields')}: ${changedFields
              .map((field) => changedFieldLabel(t, field))
              .join(' · ')}`,
          )
          const firstDiff = changedFields
            .map((field) => auditDiffLabel(t, field, item.metadata))
            .find(Boolean)
          if (firstDiff) {
            details.push(firstDiff)
          }
        }
        return details.length > 0 ? details.join(' · ') : undefined
      })(),
    })),
  }
}

export function buildStrategyOrchestrationOperationsModel({
  t,
  orchestrationStatus,
  lastResult,
}: {
  t: Translate
  orchestrationStatus?: StrategyOrchestrationStatus
  lastResult?: StrategyOrchestrationControlResult
}): StrategyOrchestrationOperationsModel {
  if (!orchestrationStatus || orchestrationStatus.entries.length === 0) {
    return {
      summary: t('workspace.strategy.registryEmpty'),
      policySummary: t('common.na'),
      rows: [],
      conflictOptions: [],
      downgradeOptions: [],
      emptyTitle: t('workspace.strategy.registryEmpty'),
      emptyHint: t('workspace.strategy.noDecisionsHint'),
    }
  }

  const statusTone =
    lastResult?.accepted === false
      ? 'danger'
      : lastResult?.accepted
        ? 'accent'
        : undefined

  return {
    summary: `${orchestrationStatus.entries.length} ${t('workspace.strategy.operationsSummarySuffix')}`,
    policySummary: `${conflictPolicyLabel(t, orchestrationStatus.conflict_policy)} · ${downgradePolicyLabel(t, orchestrationStatus.downgrade_policy)} · ${orchestrationStatus.tracked_symbols.length} ${t('workspace.strategy.trackedSymbolsSuffix')}`,
    rows: orchestrationStatus.entries.map((entry) => {
      const conflictTargets = Array.isArray(entry.conflict_targets)
        ? entry.conflict_targets
        : Array.isArray(entry.metadata.conflict_targets)
          ? (entry.metadata.conflict_targets as string[])
          : []
      const downgradeAction =
        entry.downgrade_action ||
        (typeof entry.metadata.downgrade_action === 'string' ? entry.metadata.downgrade_action : undefined)
      const currentSelectedSymbol = orchestrationStatus.tracked_symbols[0]
      return {
        id: entry.strategy_id,
        label: entry.label,
        engine: entry.engine,
        sourceLabel: sourceLabel(t, entry.source),
        roleLabel: roleLabel(t, entry.role),
        stateLabel: entry.enabled ? t('common.ready') : t('common.disabled'),
        coverageLabel: summarizeCoverage(undefined, entry.symbol_coverage),
        coverageScopeLabel: coverageScopeLabel(t, entry.coverage_scope),
        conflictTargetsLabel: conflictTargets.length > 0 ? conflictTargets.join(' · ') : t('common.na'),
        downgradeActionLabel: downgradePolicyLabel(t, downgradeAction ?? orchestrationStatus.downgrade_policy),
        impactLabel: impactLabel(t, {
          enabled: entry.enabled,
          selectedSymbol: currentSelectedSymbol,
          symbolCoverage: entry.symbol_coverage,
          executionReady: true,
        }),
        lastUpdatedLabel: formatDateTimeLabel(entry.last_updated_at),
        lastActorLabel: entry.last_actor ?? t('common.na'),
        lastReasonLabel: entry.last_reason ?? t('common.na'),
      }
    }),
    conflictOptions: [
      { id: 'review_on_conflict', label: conflictPolicyLabel(t, 'review_on_conflict') },
      { id: 'prefer_priority', label: conflictPolicyLabel(t, 'prefer_priority') },
      { id: 'prefer_weighted_score', label: conflictPolicyLabel(t, 'prefer_weighted_score') },
    ],
    downgradeOptions: [
      { id: 'review', label: downgradePolicyLabel(t, 'review') },
      { id: 'hold', label: downgradePolicyLabel(t, 'hold') },
    ],
    pendingAction: undefined,
    statusMessage: lastResult?.message,
    statusTone,
  }
}

export function buildExecutionLifecyclePanelModel({
  t,
  signal,
  persistenceStatus,
  preparedSelection,
  latestEventSummary,
  heartbeat,
  tradingPolicy,
  binanceRule,
  domainStatus,
}: {
  t: Translate
  signal?: StrategySignal
  persistenceStatus?: PersistenceStatus
  preparedSelection: PreparedExecutionSelection
  latestEventSummary: string
  heartbeat?: string
  tradingPolicy?: TradingPolicy
  binanceRule?: BinanceRule
  domainStatus: UIState
}): ExecutionLifecyclePanelModel {
  const state = domainStatus.state
  const stateLabel = lifecycleStateLabel(t, state)
  const matchingStats = persistenceStatus?.matching?.stats
  const latestLifecycleEvent = preparedSelection.latestOrder
  const partialFillCount = preparedSelection.partialFillCount
  const filledCount = preparedSelection.filledCount
  const canceledCount = preparedSelection.canceledCount
  const rejectedCount = preparedSelection.rejectedCount
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
    summaryItems: [
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
    ],
    identifierItems: [
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
    ],
    telemetryItems: [
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
