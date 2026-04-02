import type { TranslationKey } from '../../i18n/messages'
import type { DomainStatusMap } from '../../store/slices/shared'
import type { AppError, InferenceStatusPayload, PersistenceStatus, UIState } from '../../types/contracts'
import type {
  HealthCardModel,
  WorkspaceOperatorDeckSectionModel,
  WorkspaceSpotlightModel,
} from '../../view-models/workbench'
import { buildHealthCards, summarizeDomainStates } from '../../view-models/workbench'

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

function formatInferenceMode(t: Translate, inferenceStatus?: InferenceStatusPayload): string {
  const mode = inferenceStatus?.rollout?.effective_mode ?? inferenceStatus?.mode
  if (mode === 'observe') {
    return t('workspace.inference.mode.observe')
  }
  if (mode === 'primary') {
    return t('workspace.inference.mode.primary')
  }
  if (mode === 'disabled') {
    return t('workspace.inference.mode.disabled')
  }
  return mode ?? t('common.na')
}

export function buildHealthSpotlightModel({
  t,
  domainStatus,
  persistenceStatus,
  inferenceStatus,
}: {
  t: Translate
  domainStatus: DomainStatusMap
  persistenceStatus?: PersistenceStatus
  inferenceStatus?: InferenceStatusPayload
}): WorkspaceSpotlightModel {
  const domainSummary = summarizeDomainStates(domainStatus)
  const matchingStatus = persistenceStatus?.matching?.health?.status ?? t('common.disabled')

  return {
    summary: `${persistenceStatus?.status ?? t('common.disabled')} · ${matchingStatus}`,
    hint: t('workspace.health.description'),
    chips: [matchingStatus, formatInferenceMode(t, inferenceStatus)],
    accent: domainSummary.attentionCount > 0 ? 'amber' : 'teal',
    postureLabel: matchingStatus,
    metrics: [
      {
        id: 'ready-services',
        label: t('common.ready'),
        value: String(domainSummary.readyCount),
        tone: domainSummary.readyCount > 0 ? 'positive' : 'default',
        visualPriority: 'primary',
      },
      {
        id: 'attention-services',
        label: t('workspace.overview.attention'),
        value: String(domainSummary.attentionCount),
        tone: domainSummary.attentionCount > 0 ? 'negative' : 'default',
      },
      {
        id: 'processed-ticks',
        label: t('strategy.ticksProcessed'),
        value: String(persistenceStatus?.worker.processed_ticks ?? 0),
      },
      {
        id: 'rollout-mode',
        label: t('workspace.inference.rolloutMode'),
        value: formatInferenceMode(t, inferenceStatus),
        tone:
          inferenceStatus?.rollout?.effective_mode === 'primary' || inferenceStatus?.mode === 'primary'
            ? 'accent'
            : 'default',
      },
    ],
  }
}

export function buildHealthOperatorSections({
  t,
  domainStatus,
  persistenceStatus,
  inferenceStatus,
}: {
  t: Translate
  domainStatus: DomainStatusMap
  persistenceStatus?: PersistenceStatus
  inferenceStatus?: InferenceStatusPayload
}): WorkspaceOperatorDeckSectionModel[] {
  const domainSummary = summarizeDomainStates(domainStatus)
  const matchingStatus = persistenceStatus?.matching?.health?.status ?? t('common.disabled')

  return [
    {
      id: 'service-posture',
      title: t('workspace.health.operatorServiceTitle'),
      summary: t('workspace.health.operatorServiceDescription'),
      accent: domainSummary.attentionCount > 0 ? 'amber' : 'teal',
      postureLabel: formatInferenceMode(t, inferenceStatus),
      visualPriority: 'hero',
      items: [
        {
          id: 'ready-services',
          label: t('common.ready'),
          value: String(domainSummary.readyCount),
          tone: domainSummary.readyCount > 0 ? 'positive' : 'default',
        },
        {
          id: 'attention-services',
          label: t('workspace.overview.attention'),
          value: String(domainSummary.attentionCount),
          tone: domainSummary.attentionCount > 0 ? 'negative' : 'default',
        },
        {
          id: 'matching-status',
          label: t('strategy.matching'),
          value: matchingStatus,
        },
        {
          id: 'rollout-mode',
          label: t('workspace.inference.rolloutMode'),
          value: formatInferenceMode(t, inferenceStatus),
          tone:
            inferenceStatus?.rollout?.effective_mode === 'primary' || inferenceStatus?.mode === 'primary'
              ? 'accent'
              : 'default',
        },
      ],
    },
    {
      id: 'persistence-posture',
      title: t('workspace.health.operatorPersistenceTitle'),
      summary: t('workspace.health.operatorPersistenceDescription'),
      accent: 'cyan',
      postureLabel: persistenceStatus?.status ?? t('common.disabled'),
      items: [
        {
          id: 'processed-ticks',
          label: t('strategy.ticksProcessed'),
          value: String(persistenceStatus?.worker.processed_ticks ?? 0),
        },
        {
          id: 'tracked-symbols',
          label: t('workspace.health.trackedSymbols'),
          value: String(persistenceStatus?.worker.tracked_symbols?.length ?? 0),
        },
        {
          id: 'worker-started',
          label: t('workspace.health.workerStarted'),
          value: persistenceStatus?.worker.started ? t('common.yes') : t('common.no'),
        },
        {
          id: 'supabase',
          label: 'Supabase',
          value: persistenceStatus?.stores.supabase_enabled ? t('common.ready') : t('common.disabled'),
        },
        {
          id: 'firebase',
          label: 'Firestore',
          value: persistenceStatus?.stores.firebase_enabled ? t('common.ready') : t('common.disabled'),
        },
      ],
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
