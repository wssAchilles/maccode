import type { StateCreator } from 'zustand'

import { formatAppError, requestEnvelope, toAppError } from '../../lib/http'
import type {
  AppError,
  Envelope,
  InferenceCatalogResponse,
  InferenceControlResult,
  StrategySummaryResponse,
} from '../../types/contracts'
import type { RootStore, StrategySummarySlice } from './shared'

function envelopeError<T>(scope: string, envelope: Envelope<T>): AppError | null {
  if (envelope.ok) {
    return null
  }
  const normalized = toAppError(envelope.error, `${scope}_error`)
  return {
    ...normalized,
    code: `${scope}.${normalized.code}`,
    message: `[${envelope.status_code}] ${normalized.message}`,
  }
}

function resolveSummaryErrors(summary: StrategySummaryResponse): AppError[] {
  return [
    envelopeError('signal', summary.signal),
    envelopeError('recent_signals', summary.recent_signals),
    envelopeError('persistence', summary.persistence),
    envelopeError('matching_orderbook', summary.matching_orderbook),
    envelopeError('inference_status', summary.inference_status),
  ].filter((value): value is AppError => Boolean(value))
}

function aggregateSummaryError(errors: AppError[]): AppError | undefined {
  if (errors.length === 0) {
    return undefined
  }
  return {
    code: 'partial_upstream_failure',
    message: errors.map((error) => formatAppError(error)).join(' | '),
    request_id: errors.find((error) => Boolean(error.request_id))?.request_id,
  }
}

function operatorBody(reason?: string): string {
  return JSON.stringify({
    actor: 'workspace.operator',
    reason: reason?.trim() || undefined,
  })
}

function withInferencePending(
  set: Parameters<StateCreator<RootStore, [], [], StrategySummarySlice>>[0],
  pendingAction?: string,
) {
  set((state) => ({
    strategySummary: {
      ...state.strategySummary,
      inference_pending_action: pendingAction,
    },
  }))
}

function withInferenceResult(
  set: Parameters<StateCreator<RootStore, [], [], StrategySummarySlice>>[0],
  result?: InferenceControlResult,
  error?: AppError,
) {
  set((state) => ({
    strategySummary: {
      ...state.strategySummary,
      inference_last_result: result,
      last_error: error ?? state.strategySummary.last_error,
      inference_pending_action: undefined,
    },
  }))
}

export const createStrategySummarySlice: StateCreator<RootStore, [], [], StrategySummarySlice> = (
  set,
  get,
) => ({
  strategySummary: {
    signal: undefined,
    recent_signals: [],
    persistence_status: undefined,
    matching_orderbook: undefined,
    inference_status: undefined,
    inference_catalog: undefined,
    inference_last_result: undefined,
    inference_pending_action: undefined,
    last_error: undefined,
  },
  strategySummaryActions: {
    refreshSummary: async () => {
      const { env, marketStream } = get()
      const symbol = marketStream.selected_symbol

      get().uiActions.setDomainStatus('strategy-summary', {
        state: 'loading',
        stale: false,
        reason: undefined,
        request_id: undefined,
      })

      const response = await requestEnvelope<StrategySummaryResponse>(
        `${env.gateway_base}/api/v1/strategy/summary?symbol=${encodeURIComponent(
          symbol,
        )}&recent_limit=8&source=auto&orderbook_depth=10`,
      )

      if (!response.ok || !response.payload) {
        const error = toAppError(response.error, 'strategy_summary_failed')
        set((state) => ({
          strategySummary: {
            ...state.strategySummary,
            last_error: error,
          },
        }))
        get().uiActions.setDomainStatus('strategy-summary', {
          state: 'error',
          stale: true,
          reason: formatAppError(error),
          request_id: error.request_id,
        })
        return
      }

      const summary = response.payload
      const errors = resolveSummaryErrors(summary)
      const mergedError = aggregateSummaryError(errors)
      const status = errors.length > 0 ? 'degraded' : 'ready'

      set((state) => ({
        strategySummary: {
          ...state.strategySummary,
          signal: summary.signal.ok ? summary.signal.payload : undefined,
          recent_signals: summary.recent_signals.ok
            ? summary.recent_signals.payload?.signals ?? []
            : [],
          persistence_status: summary.persistence.ok ? summary.persistence.payload : undefined,
          matching_orderbook: summary.matching_orderbook.ok
            ? summary.matching_orderbook.payload
            : undefined,
          inference_status: summary.inference_status.ok
            ? summary.inference_status.payload
            : undefined,
          inference_last_result: state.strategySummary.inference_last_result,
          inference_catalog: state.strategySummary.inference_catalog,
          inference_pending_action: state.strategySummary.inference_pending_action,
          last_error: mergedError,
        },
      }))

      get().uiActions.setDomainStatus('strategy-summary', {
        state: status,
        stale: false,
        reason: mergedError ? formatAppError(mergedError) : undefined,
        request_id: mergedError?.request_id ?? summary.request_id,
      })
    },
    loadInferenceCatalog: async () => {
      const { env } = get()
      const response = await requestEnvelope<InferenceCatalogResponse>(
        `${env.gateway_base}/api/v1/inference/models`,
      )
      if (!response.ok || !response.payload) {
        return
      }
      set((state) => ({
        strategySummary: {
          ...state.strategySummary,
          inference_catalog: response.payload,
        },
      }))
    },
    requestInferencePromotion: async (reason?: string) => {
      const { env } = get()
      withInferencePending(set, 'promote')
      const response = await requestEnvelope<InferenceControlResult>(
        `${env.gateway_base}/api/v1/inference/rollout/promote`,
        {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: operatorBody(reason),
        },
      )
      if (!response.ok || !response.payload) {
        withInferenceResult(set, undefined, toAppError(response.error, 'inference_promote_failed'))
        return
      }
      withInferenceResult(set, response.payload)
      await get().strategySummaryActions.refreshSummary()
      await get().strategySummaryActions.loadInferenceCatalog()
    },
    requestInferenceRollback: async (reason?: string) => {
      const { env } = get()
      withInferencePending(set, 'rollback')
      const response = await requestEnvelope<InferenceControlResult>(
        `${env.gateway_base}/api/v1/inference/rollout/rollback`,
        {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: operatorBody(reason),
        },
      )
      if (!response.ok || !response.payload) {
        withInferenceResult(set, undefined, toAppError(response.error, 'inference_rollback_failed'))
        return
      }
      withInferenceResult(set, response.payload)
      await get().strategySummaryActions.refreshSummary()
      await get().strategySummaryActions.loadInferenceCatalog()
    },
    activateInferenceModel: async (modelId: string, version?: string, reason?: string) => {
      const { env } = get()
      withInferencePending(set, 'activate_model')
      const response = await requestEnvelope<InferenceControlResult>(
        `${env.gateway_base}/api/v1/inference/models/activate`,
        {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            model_id: modelId,
            version: version || undefined,
            actor: 'workspace.operator',
            reason: reason?.trim() || undefined,
          }),
        },
      )
      if (!response.ok || !response.payload) {
        withInferenceResult(set, undefined, toAppError(response.error, 'inference_model_activate_failed'))
        return
      }
      withInferenceResult(set, response.payload)
      await get().strategySummaryActions.refreshSummary()
      await get().strategySummaryActions.loadInferenceCatalog()
    },
  },
})
