import type { TranslationKey } from '../../i18n/messages'
import type { AppError, PersistenceStatus, UIState } from '../../types/contracts'

type Translate = (key: TranslationKey) => string

export type HealthDataItem = {
  id: string
  label: string
  value: string
}

export type HealthDiagnosticsModel = {
  summaryError?: AppError
  domainStatus: Record<string, UIState>
}

type BuildHealthItemsParams = {
  t: Translate
  persistenceStatus?: PersistenceStatus
}

export function buildHealthWorkerItems({
  t,
  persistenceStatus,
}: BuildHealthItemsParams): HealthDataItem[] {
  return [
    {
      id: 'processed',
      label: t('strategy.ticksProcessed'),
      value: String(persistenceStatus?.worker.processed_ticks ?? 0),
    },
    {
      id: 'trackedSymbols',
      label: t('workspace.health.trackedSymbols'),
      value: String(persistenceStatus?.worker.tracked_symbols?.length ?? 0),
    },
    {
      id: 'started',
      label: t('workspace.health.workerStarted'),
      value: String(persistenceStatus?.worker.started ?? false),
    },
  ]
}

export function buildHealthStoreItems({
  t,
  persistenceStatus,
}: BuildHealthItemsParams): HealthDataItem[] {
  return [
    {
      id: 'supabase',
      label: 'Supabase',
      value: String(persistenceStatus?.stores.supabase_enabled ?? false),
    },
    {
      id: 'firebase',
      label: 'Firestore',
      value: String(persistenceStatus?.stores.firebase_enabled ?? false),
    },
    {
      id: 'matching',
      label: t('strategy.matching'),
      value: persistenceStatus?.matching?.health?.status ?? t('common.disabled'),
    },
  ]
}

export function buildHealthDiagnostics(
  summaryError: AppError | undefined,
  domainStatus: Record<string, UIState>,
): HealthDiagnosticsModel {
  return {
    summaryError,
    domainStatus,
  }
}
