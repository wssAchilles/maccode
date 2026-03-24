import type { TranslationKey } from '../../i18n/messages'

export type GatewayResponse = {
  status: number
  at: string
  body: unknown
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
