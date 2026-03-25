import type { TranslationKey } from '../../i18n/messages'
import type { AppError } from '../../types/contracts'

export type GatewayResponse = {
  status: number
  at: string
  body: unknown
  error?: AppError
}

export type Stage = 'idle' | 'prechecked' | 'submitting' | 'submitted' | 'rejected'

export const STAGE_KEY_MAP: Record<Stage, TranslationKey> = {
  idle: 'execution.stage.idle',
  prechecked: 'execution.stage.prechecked',
  submitting: 'execution.stage.submitting',
  submitted: 'execution.stage.submitted',
  rejected: 'execution.stage.rejected',
}

export function parsePositiveNumber(input: string): number | null {
  const value = Number(input)
  if (!Number.isFinite(value) || value <= 0) {
    return null
  }
  return value
}

export function readGatewayRequestId(body: unknown): string | undefined {
  if (!body || typeof body !== 'object') {
    return undefined
  }
  const envelope = body as { request_id?: unknown; data?: unknown; error?: unknown }
  if ('data' in envelope && 'error' in envelope) {
    if (typeof envelope.request_id === 'string' && envelope.request_id.trim().length > 0) {
      return envelope.request_id
    }
  }
  const direct = (body as { request_id?: unknown }).request_id
  if (typeof direct === 'string' && direct.trim().length > 0) {
    return direct
  }

  const nested = (body as { error?: { request_id?: unknown } }).error?.request_id
  if (typeof nested === 'string' && nested.trim().length > 0) {
    return nested
  }

  return undefined
}
