import type { TranslationKey } from '../../i18n/messages'
import type { DomainStatusMap } from '../../store/slices/shared'
import type { AppError, PersistenceStatus, UIState } from '../../types/contracts'
import type { HealthCardModel } from '../../view-models/workbench'
import { buildHealthCards } from '../../view-models/workbench'

type Translate = (key: TranslationKey) => string

export type HealthDataItem = {
  id: string
  label: string
  value: string
}

export type ServiceHealthPanelModel = {
  cards: HealthCardModel[]
  updatedAtLabel: string
  requestIdLabel: string
  persistenceGroups: HealthDataItem[][]
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

export function buildServiceHealthPanelModel({
  t,
  domainStatus,
  persistenceStatus,
}: {
  t: Translate
  domainStatus: DomainStatusMap
  persistenceStatus?: PersistenceStatus
}): ServiceHealthPanelModel {
  const persistenceGroups = persistenceStatus
    ? [
        [
          { id: 'status', label: t('strategy.persistence'), value: persistenceStatus.status },
          {
            id: 'ticks',
            label: t('strategy.ticksProcessed'),
            value: String(persistenceStatus.worker.processed_ticks),
          },
          {
            id: 'supabase',
            label: 'Supabase',
            value: persistenceStatus.stores.supabase_enabled ? t('common.ready') : t('common.disabled'),
          },
          {
            id: 'firebase',
            label: 'Firestore',
            value: persistenceStatus.stores.firebase_enabled ? t('common.ready') : t('common.disabled'),
          },
        ],
        [
          {
            id: 'matchingStatus',
            label: t('strategy.matching'),
            value: persistenceStatus.matching?.health?.status ?? t('common.disabled'),
          },
          {
            id: 'liveOrders',
            label: 'Live orders',
            value: String(persistenceStatus.matching?.stats?.live_orders ?? 0),
          },
          {
            id: 'trades',
            label: 'Trades',
            value: String(persistenceStatus.matching?.stats?.trade_count ?? 0),
          },
          {
            id: 'symbols',
            label: 'Symbols',
            value: String(persistenceStatus.matching?.stats?.symbols ?? 0),
          },
        ],
      ]
    : []

  return {
    cards: buildHealthCards(domainStatus, t),
    updatedAtLabel: t('common.updatedAt'),
    requestIdLabel: t('health.requestId'),
    persistenceGroups,
  }
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
