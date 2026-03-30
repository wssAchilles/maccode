import type { TranslationKey } from '../../i18n/messages'
import type { InferenceModelDescriptor, InferenceStatusPayload, LoadState } from '../../types/contracts'

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

export type InferenceDiagnosticsModel = {
  state: LoadState
  stateLabel: string
  summary: string
  reason?: string
  runtimeItems: InferenceDataItem[]
  modelItems: InferenceDataItem[]
}

type InferenceModelParams = {
  t: Translate
  inferenceStatus?: InferenceStatusPayload
}

const MODE_LABELS: Record<string, TranslationKey> = {
  observe: 'workspace.inference.mode.observe',
  primary: 'workspace.inference.mode.primary',
  disabled: 'workspace.inference.mode.disabled',
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

function compactSymbolCoverage(t: Translate, model?: InferenceModelDescriptor | null): string {
  if (!model || model.symbols.length === 0) {
    return t('common.na')
  }
  return `${model.symbols.length}`
}

function detailedSymbolCoverage(t: Translate, model?: InferenceModelDescriptor | null): string {
  if (!model || model.symbols.length === 0) {
    return t('common.na')
  }
  return model.symbols.join(', ')
}

function formatMacroF1(value: number | undefined, t: Translate): string {
  if (value === undefined) {
    return t('common.na')
  }
  return value.toFixed(3)
}

function formatInteger(value: number | undefined, t: Translate): string {
  if (value === undefined || value <= 0) {
    return t('common.na')
  }
  return String(value)
}

export function buildInferenceStatusCardModel({
  t,
  inferenceStatus,
}: InferenceModelParams): InferenceStatusCardModel {
  const state = resolveLoadState(inferenceStatus)
  const stateLabel = resolveStateLabel(t, state, inferenceStatus)
  const model = inferenceStatus?.active_model
  const modelMetadata = model?.metadata
  const macroF1 = readNumber(modelMetadata, 'best_macro_f1')
  const lookback = readNumber(modelMetadata, 'lookback') ?? readNumber(inferenceStatus?.metadata, 'lookback')

  return {
    state,
    stateLabel,
    summary: modelSummary(t, model),
    reason: inferenceStatus?.reason ?? undefined,
    items: [
      {
        id: 'mode',
        label: t('workspace.inference.rolloutMode'),
        value: formatMode(t, inferenceStatus?.mode),
      },
      {
        id: 'engine',
        label: t('workspace.inference.engine'),
        value: inferenceStatus?.engine ?? t('common.na'),
      },
      {
        id: 'coverage',
        label: t('workspace.inference.symbolCoverage'),
        value: compactSymbolCoverage(t, model),
      },
      {
        id: 'macroF1',
        label: t('workspace.inference.macroF1'),
        value: formatMacroF1(macroF1, t),
        tone: macroF1 !== undefined ? 'accent' : 'default',
      },
      {
        id: 'lookback',
        label: t('workspace.inference.lookback'),
        value: formatInteger(lookback, t),
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
  const lookback = readNumber(modelMetadata, 'lookback') ?? readNumber(runtimeMetadata, 'lookback')
  const horizon = readNumber(modelMetadata, 'horizon') ?? readNumber(runtimeMetadata, 'horizon')
  const macroF1 = readNumber(modelMetadata, 'best_macro_f1')

  return {
    state,
    stateLabel,
    summary: modelSummary(t, model),
    reason: inferenceStatus?.reason ?? undefined,
    runtimeItems: [
      {
        id: 'runtimeStatus',
        label: t('workspace.inference.runtimeStatus'),
        value: stateLabel,
        tone: state === 'ready' ? 'accent' : 'default',
      },
      {
        id: 'rollout',
        label: t('workspace.inference.rolloutMode'),
        value: formatMode(t, inferenceStatus?.mode),
      },
      {
        id: 'engine',
        label: t('workspace.inference.engine'),
        value: inferenceStatus?.engine ?? t('common.na'),
      },
      {
        id: 'reason',
        label: t('workspace.inference.reason'),
        value: inferenceStatus?.reason ?? t('common.na'),
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
        value: detailedSymbolCoverage(t, model),
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
  }
}
