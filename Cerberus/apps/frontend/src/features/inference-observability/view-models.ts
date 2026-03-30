import type { TranslationKey } from '../../i18n/messages'
import type {
  InferenceAuditEvent,
  InferenceCatalogResponse,
  InferenceComparisonPayload,
  InferenceControlResult,
  InferenceModelDescriptor,
  InferenceRolloutPayload,
  InferenceStatusPayload,
  InferenceSymbolComparison,
  LoadState,
} from '../../types/contracts'

type Translate = (key: TranslationKey) => string

export type InferenceDataItem = {
  id: string
  label: string
  value: string
  tone?: 'default' | 'muted' | 'accent'
}

export type InferenceStatusCardModel = {
  state: LoadState
  stateLabel: string
  summary: string
  reason?: string
  items: InferenceDataItem[]
}

export type InferenceSignalDistributionGroup = {
  id: string
  label: string
  items: InferenceDataItem[]
}

export type InferenceSymbolComparisonModel = {
  id: string
  symbol: string
  comparedTicks: string
  agreementRate: string
  divergenceCount: string
  tone?: 'default' | 'muted' | 'accent'
}

export type InferenceAuditTimelineEntry = {
  id: string
  title: string
  message: string
  createdAt: string
  detail?: string
}

export type InferenceDiagnosticsModel = {
  state: LoadState
  stateLabel: string
  summary: string
  reason?: string
  runtimeItems: InferenceDataItem[]
  rolloutItems: InferenceDataItem[]
  comparisonItems: InferenceDataItem[]
  modelItems: InferenceDataItem[]
  auditItems: InferenceDataItem[]
  signalDistributions: InferenceSignalDistributionGroup[]
  symbolComparisons: InferenceSymbolComparisonModel[]
  auditTimeline: InferenceAuditTimelineEntry[]
}

export type InferenceModelOption = {
  id: string
  label: string
  active: boolean
}

export type InferenceOperationsModel = {
  state: LoadState
  stateLabel: string
  targetModeLabel: string
  effectiveModeLabel: string
  summary: string
  blockers: string[]
  pendingAction?: string
  statusMessage?: string
  statusTone?: 'default' | 'accent' | 'danger'
  canPromote: boolean
  canRollback: boolean
  canActivateModel: boolean
  selectedModelId: string
  modelOptions: InferenceModelOption[]
}

type InferenceModelParams = {
  t: Translate
  inferenceStatus?: InferenceStatusPayload
}

type InferenceOperationsParams = InferenceModelParams & {
  catalog?: InferenceCatalogResponse
  lastResult?: InferenceControlResult
  selectedModelId: string
}

const MODE_LABELS: Record<string, TranslationKey> = {
  observe: 'workspace.inference.mode.observe',
  primary: 'workspace.inference.mode.primary',
  disabled: 'workspace.inference.mode.disabled',
}

const BLOCKER_LABELS: Record<string, TranslationKey> = {
  no_active_model: 'workspace.inference.blocker.noActiveModel',
  macro_f1_missing: 'workspace.inference.blocker.macroF1Missing',
  offline_macro_f1_below_threshold: 'workspace.inference.blocker.offlineMacroF1',
  insufficient_observe_ticks: 'workspace.inference.blocker.observeTicks',
  agreement_ratio_unavailable: 'workspace.inference.blocker.agreementUnavailable',
  agreement_ratio_below_threshold: 'workspace.inference.blocker.agreementBelow',
}

const AUDIT_EVENT_LABELS: Record<string, TranslationKey> = {
  rollout_initialized: 'workspace.inference.auditEvent.rolloutInitialized',
  rollout_holdback: 'workspace.inference.auditEvent.rolloutHoldback',
  rollout_transition: 'workspace.inference.auditEvent.rolloutTransition',
  rollout_blockers_changed: 'workspace.inference.auditEvent.rolloutBlockersChanged',
  comparison_milestone: 'workspace.inference.auditEvent.comparisonMilestone',
  rollout_resumed: 'workspace.inference.auditEvent.rolloutResumed',
  rollout_restore_skipped: 'workspace.inference.auditEvent.rolloutRestoreSkipped',
  rollout_state_degraded: 'workspace.inference.auditEvent.rolloutStateDegraded',
  rollout_target_changed: 'workspace.inference.auditEvent.rolloutTargetChanged',
  rollout_target_noop: 'workspace.inference.auditEvent.rolloutTargetNoop',
  active_model_changed: 'workspace.inference.auditEvent.activeModelChanged',
  model_activation_noop: 'workspace.inference.auditEvent.modelActivationNoop',
}

function resolveLoadState(inferenceStatus?: InferenceStatusPayload): LoadState {
  if (!inferenceStatus) {
    return 'idle'
  }
  if (!inferenceStatus.enabled) {
    return 'idle'
  }
  if (inferenceStatus.ready) {
    return 'ready'
  }
  if (inferenceStatus.reason) {
    return 'degraded'
  }
  return 'loading'
}

function resolveStateLabel(t: Translate, state: LoadState, inferenceStatus?: InferenceStatusPayload): string {
  if (inferenceStatus && !inferenceStatus.enabled) {
    return t('common.disabled')
  }
  if (state === 'idle') {
    return t('health.state.idle')
  }
  if (state === 'loading') {
    return t('health.state.loading')
  }
  if (state === 'ready') {
    return t('common.ready')
  }
  if (state === 'degraded') {
    return t('health.state.degraded')
  }
  return t('health.state.error')
}

function formatMode(t: Translate, mode?: string): string {
  if (!mode) {
    return t('common.na')
  }
  return MODE_LABELS[mode] ? t(MODE_LABELS[mode]) : mode
}

function modelSummary(t: Translate, model?: InferenceModelDescriptor | null): string {
  if (!model) {
    return t('workspace.inference.noModel')
  }
  return `${model.model_id} · ${model.version}`
}

function readNumber(metadata: Record<string, unknown> | undefined, key: string): number | undefined {
  const value = metadata?.[key]
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  return undefined
}

function formatMacroF1(value: number | undefined, t: Translate): string {
  if (value === undefined) {
    return t('common.na')
  }
  return value.toFixed(3)
}

function formatInteger(value: number | undefined, t: Translate): string {
  if (value === undefined || value < 0) {
    return t('common.na')
  }
  return String(value)
}

function formatPercent(value: number | undefined | null, t: Translate): string {
  if (value === undefined || value === null || !Number.isFinite(value)) {
    return t('common.na')
  }
  return `${(value * 100).toFixed(1)}%`
}

function formatDateTime(value: string | undefined, t: Translate): string {
  if (!value) {
    return t('common.na')
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return parsed.toLocaleString()
}

function formatBoolean(value: boolean | undefined, t: Translate): string {
  if (value === undefined) {
    return t('common.na')
  }
  return value ? t('common.yes') : t('common.no')
}

function translateBlocker(t: Translate, blocker: string): string {
  return BLOCKER_LABELS[blocker] ? t(BLOCKER_LABELS[blocker]) : blocker
}

function blockersSummary(t: Translate, rollout?: InferenceRolloutPayload): string | undefined {
  if (!rollout || rollout.blockers.length === 0) {
    return undefined
  }
  return rollout.blockers.map((blocker) => translateBlocker(t, blocker)).join(' · ')
}

function comparisonSummary(t: Translate, comparison?: InferenceComparisonPayload): string {
  if (!comparison || comparison.compared_ticks <= 0) {
    return t('workspace.inference.comparisonPending')
  }
  return `${formatPercent(comparison.agreement_ratio, t)} · ${comparison.compared_ticks} ${t('workspace.inference.comparedTicks').toLowerCase()}`
}

function latestAudit(audit?: InferenceAuditEvent[]): InferenceAuditEvent | undefined {
  if (!audit || audit.length === 0) {
    return undefined
  }
  return audit[audit.length - 1]
}

function promotionStateLabel(t: Translate, rollout?: InferenceRolloutPayload): string {
  if (!rollout) {
    return t('common.na')
  }
  if (rollout.configured_mode !== 'primary') {
    return t('workspace.inference.promotionNotRequested')
  }
  if (rollout.effective_mode === 'primary') {
    return t('workspace.inference.promotionReady')
  }
  return t('workspace.inference.promotionHeld')
}

function auditEventTitle(t: Translate, event: InferenceAuditEvent): string {
  return AUDIT_EVENT_LABELS[event.event_type] ? t(AUDIT_EVENT_LABELS[event.event_type]) : event.event_type
}

function auditEventDetail(t: Translate, event: InferenceAuditEvent): string | undefined {
  const parts: string[] = []
  const blockers = event.metadata.blockers
  if (Array.isArray(blockers) && blockers.length > 0) {
    parts.push(blockers.map((blocker) => translateBlocker(t, String(blocker))).join(' · '))
  }
  const currentBlockers = event.metadata.current_blockers
  if (Array.isArray(currentBlockers) && currentBlockers.length > 0) {
    parts.push(currentBlockers.map((blocker) => translateBlocker(t, String(blocker))).join(' · '))
  }
  const previousBlockers = event.metadata.previous_blockers
  if (Array.isArray(previousBlockers) && previousBlockers.length > 0) {
    parts.push(previousBlockers.map((blocker) => translateBlocker(t, String(blocker))).join(' · '))
  }
  const milestone = event.metadata.milestone
  if (typeof milestone === 'number') {
    parts.push(`${formatInteger(milestone, t)} ${t('workspace.inference.comparedTicks').toLowerCase()}`)
  }
  const backend = event.metadata.backend
  if (typeof backend === 'string' && backend.length > 0) {
    parts.push(`${t('workspace.inference.stateBackend')}: ${backend}`)
  }
  const reason = event.metadata.reason
  if (typeof reason === 'string' && reason.length > 0) {
    parts.push(reason)
  }
  const action = event.metadata.action
  if (typeof action === 'string' && action.length > 0) {
    parts.push(action)
  }
  return parts.length > 0 ? parts.join(' · ') : undefined
}

function buildSignalDistribution(
  t: Translate,
  comparison?: InferenceComparisonPayload,
): InferenceSignalDistributionGroup[] {
  if (!comparison) {
    return []
  }

  const toItems = (counts: Record<string, number>, prefixKey: TranslationKey, idPrefix: string): InferenceDataItem[] => {
    const entries = Object.entries(counts).sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    return entries.map(([signal, count]) => ({
      id: `${idPrefix}-${signal}`,
      label: `${t(prefixKey)} · ${signal}`,
      value: String(count),
    }))
  }

  const groups: InferenceSignalDistributionGroup[] = []
  const ruleItems = toItems(comparison.rule_signal_counts, 'workspace.inference.ruleSignals', 'rule')
  if (ruleItems.length > 0) {
    groups.push({
      id: 'rule-signals',
      label: t('workspace.inference.ruleSignals'),
      items: ruleItems,
    })
  }
  const inferenceItems = toItems(comparison.inference_signal_counts, 'workspace.inference.inferenceSignals', 'inference')
  if (inferenceItems.length > 0) {
    groups.push({
      id: 'inference-signals',
      label: t('workspace.inference.inferenceSignals'),
      items: inferenceItems,
    })
  }
  return groups
}

function buildSymbolComparisons(
  t: Translate,
  comparison?: InferenceComparisonPayload,
): InferenceSymbolComparisonModel[] {
  if (!comparison || comparison.symbols.length === 0) {
    return []
  }
  return comparison.symbols.map((entry: InferenceSymbolComparison) => ({
    id: entry.symbol,
    symbol: entry.symbol,
    comparedTicks: formatInteger(entry.compared_ticks, t),
    agreementRate: formatPercent(entry.agreement_ratio, t),
    divergenceCount: formatInteger(entry.divergence_count, t),
    tone:
      entry.agreement_ratio !== undefined && entry.agreement_ratio !== null && entry.agreement_ratio >= 0.55
        ? 'accent'
        : 'default',
  }))
}

function buildAuditTimeline(
  t: Translate,
  audit?: InferenceAuditEvent[],
): InferenceAuditTimelineEntry[] {
  if (!audit || audit.length === 0) {
    return []
  }
  return [...audit]
    .reverse()
    .map((event, index) => ({
      id: `${event.event_type}-${event.created_at}-${index}`,
      title: auditEventTitle(t, event),
      message: event.message,
      createdAt: formatDateTime(event.created_at, t),
      detail: auditEventDetail(t, event),
    }))
}

export function buildInferenceStatusCardModel({
  t,
  inferenceStatus,
}: InferenceModelParams): InferenceStatusCardModel {
  const state = resolveLoadState(inferenceStatus)
  const stateLabel = resolveStateLabel(t, state, inferenceStatus)
  const model = inferenceStatus?.active_model
  const modelMetadata = model?.metadata
  const rollout = inferenceStatus?.rollout
  const comparison = inferenceStatus?.comparison
  const macroF1 = readNumber(modelMetadata, 'best_macro_f1')

  return {
    state,
    stateLabel,
    summary: modelSummary(t, model),
    reason: blockersSummary(t, rollout) ?? inferenceStatus?.reason ?? undefined,
    items: [
      {
        id: 'mode',
        label: t('workspace.inference.rolloutMode'),
        value: formatMode(t, rollout?.effective_mode ?? inferenceStatus?.mode),
      },
      {
        id: 'promotion',
        label: t('workspace.inference.promotionState'),
        value: promotionStateLabel(t, rollout),
      },
      {
        id: 'comparedTicks',
        label: t('workspace.inference.comparedTicks'),
        value: formatInteger(comparison?.compared_ticks, t),
      },
      {
        id: 'agreementRate',
        label: t('workspace.inference.agreementRate'),
        value: formatPercent(comparison?.agreement_ratio, t),
        tone: comparison?.agreement_ratio !== undefined && comparison?.agreement_ratio !== null ? 'accent' : 'default',
      },
      {
        id: 'macroF1',
        label: t('workspace.inference.macroF1'),
        value: formatMacroF1(macroF1, t),
        tone: macroF1 !== undefined ? 'accent' : 'default',
      },
    ],
  }
}

export function buildInferenceDiagnosticsModel({
  t,
  inferenceStatus,
}: InferenceModelParams): InferenceDiagnosticsModel {
  const state = resolveLoadState(inferenceStatus)
  const stateLabel = resolveStateLabel(t, state, inferenceStatus)
  const model = inferenceStatus?.active_model
  const modelMetadata = model?.metadata
  const runtimeMetadata = inferenceStatus?.metadata
  const rollout = inferenceStatus?.rollout
  const comparison = inferenceStatus?.comparison
  const audit = latestAudit(inferenceStatus?.audit)
  const lookback = readNumber(modelMetadata, 'lookback') ?? readNumber(runtimeMetadata, 'lookback')
  const horizon = readNumber(modelMetadata, 'horizon') ?? readNumber(runtimeMetadata, 'horizon')
  const macroF1 = readNumber(modelMetadata, 'best_macro_f1')
  const blockers = blockersSummary(t, rollout)

  return {
    state,
    stateLabel,
    summary: modelSummary(t, model),
    reason: blockers ?? inferenceStatus?.reason ?? undefined,
    runtimeItems: [
      {
        id: 'runtimeStatus',
        label: t('workspace.inference.runtimeStatus'),
        value: stateLabel,
        tone: state === 'ready' ? 'accent' : 'default',
      },
      {
        id: 'configuredMode',
        label: t('workspace.inference.configuredMode'),
        value: formatMode(t, rollout?.configured_mode ?? inferenceStatus?.mode),
      },
      {
        id: 'effectiveMode',
        label: t('workspace.inference.rolloutMode'),
        value: formatMode(t, rollout?.effective_mode ?? inferenceStatus?.mode),
      },
      {
        id: 'engine',
        label: t('workspace.inference.engine'),
        value: inferenceStatus?.engine ?? t('common.na'),
      },
      {
        id: 'stateBackend',
        label: t('workspace.inference.stateBackend'),
        value: rollout?.state_backend ?? t('common.na'),
      },
      {
        id: 'stateRestored',
        label: t('workspace.inference.stateRestored'),
        value: formatBoolean(rollout?.state_restored, t),
      },
    ],
    rolloutItems: [
      {
        id: 'promotion',
        label: t('workspace.inference.promotionState'),
        value: promotionStateLabel(t, rollout),
        tone: rollout?.effective_mode === 'primary' ? 'accent' : 'default',
      },
      {
        id: 'requiredObserveTicks',
        label: t('workspace.inference.requiredObserveTicks'),
        value: formatInteger(rollout?.required_observe_ticks, t),
      },
      {
        id: 'requiredAgreement',
        label: t('workspace.inference.requiredAgreementRate'),
        value: formatPercent(rollout?.required_agreement_ratio, t),
      },
      {
        id: 'requiredMacroF1',
        label: t('workspace.inference.requiredMacroF1'),
        value: formatMacroF1(rollout?.required_macro_f1, t),
      },
      {
        id: 'rolloutStartedAt',
        label: t('workspace.inference.rolloutStartedAt'),
        value: formatDateTime(rollout?.started_at, t),
      },
      {
        id: 'lastTransitionAt',
        label: t('workspace.inference.lastTransitionAt'),
        value: formatDateTime(rollout?.last_transition_at, t),
      },
      {
        id: 'lastPersistedAt',
        label: t('workspace.inference.lastPersistedAt'),
        value: formatDateTime(rollout?.last_persisted_at, t),
      },
    ],
    comparisonItems: [
      {
        id: 'comparedTicks',
        label: t('workspace.inference.comparedTicks'),
        value: formatInteger(comparison?.compared_ticks, t),
      },
      {
        id: 'observedTicks',
        label: t('workspace.inference.observedTicks'),
        value: formatInteger(comparison?.observed_ticks, t),
      },
      {
        id: 'agreementRate',
        label: t('workspace.inference.agreementRate'),
        value: formatPercent(comparison?.agreement_ratio, t),
        tone: comparison?.agreement_ratio !== undefined && comparison?.agreement_ratio !== null ? 'accent' : 'default',
      },
      {
        id: 'divergenceCount',
        label: t('workspace.inference.divergenceCount'),
        value: formatInteger(comparison?.divergence_count, t),
      },
      {
        id: 'comparisonSummary',
        label: t('workspace.inference.comparisonSummary'),
        value: comparisonSummary(t, comparison),
      },
    ],
    modelItems: [
      {
        id: 'model',
        label: t('workspace.inference.model'),
        value: modelSummary(t, model),
      },
      {
        id: 'symbols',
        label: t('workspace.inference.symbolCoverage'),
        value: model && model.symbols.length > 0 ? model.symbols.join(', ') : t('common.na'),
      },
      {
        id: 'lookback',
        label: t('workspace.inference.lookback'),
        value: formatInteger(lookback, t),
      },
      {
        id: 'horizon',
        label: t('workspace.inference.horizon'),
        value: formatInteger(horizon, t),
      },
      {
        id: 'macroF1',
        label: t('workspace.inference.macroF1'),
        value: formatMacroF1(macroF1, t),
        tone: macroF1 !== undefined ? 'accent' : 'default',
      },
    ],
    auditItems: [
      {
        id: 'event',
        label: t('workspace.inference.recentAudit'),
        value: audit?.message ?? t('workspace.inference.auditEmpty'),
      },
      {
        id: 'auditAt',
        label: t('workspace.inference.lastTransitionAt'),
        value: formatDateTime(audit?.created_at, t),
      },
      {
        id: 'blockers',
        label: t('workspace.inference.gateBlockers'),
        value: blockers ?? t('common.na'),
      },
    ],
    signalDistributions: buildSignalDistribution(t, comparison),
    symbolComparisons: buildSymbolComparisons(t, comparison),
    auditTimeline: buildAuditTimeline(t, inferenceStatus?.audit),
  }
}

export function buildInferenceOperationsModel({
  t,
  inferenceStatus,
  catalog,
  lastResult,
  selectedModelId,
}: InferenceOperationsParams): InferenceOperationsModel {
  const state = resolveLoadState(inferenceStatus)
  const stateLabel = resolveStateLabel(t, state, inferenceStatus)
  const rollout = inferenceStatus?.rollout
  const targetMode = rollout?.target_mode ?? inferenceStatus?.mode
  const effectiveMode = rollout?.effective_mode ?? inferenceStatus?.mode
  const activeModel = catalog?.active_model ?? inferenceStatus?.active_model ?? null
  const blockers = rollout?.blockers?.map((blocker) => translateBlocker(t, blocker)) ?? []
  const modelOptions = (catalog?.models ?? []).map((model) => {
    const id = `${model.model_id}:${model.version}`
    const active =
      activeModel?.model_id === model.model_id && activeModel?.version === model.version
    return {
      id,
      label: `${model.model_id} · ${model.version}`,
      active,
    }
  })
  const statusTone =
    lastResult == null
      ? undefined
      : lastResult.accepted
        ? 'accent'
        : 'danger'

  return {
    state,
    stateLabel,
    targetModeLabel: formatMode(t, targetMode),
    effectiveModeLabel: formatMode(t, effectiveMode),
    summary: modelSummary(t, activeModel),
    blockers,
    pendingAction: undefined,
    statusMessage: lastResult?.message,
    statusTone,
    canPromote: state === 'ready' && targetMode !== 'primary',
    canRollback: state !== 'idle' && targetMode !== 'observe',
    canActivateModel:
      modelOptions.length > 1 &&
      selectedModelId.trim().length > 0 &&
      selectedModelId !== `${activeModel?.model_id ?? ''}:${activeModel?.version ?? ''}`,
    selectedModelId,
    modelOptions,
  }
}
