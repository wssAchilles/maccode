import type { TranslationKey } from '../../i18n/messages'
import type { DomainStatusMap } from '../../store/slices/shared'
import type { AppError, InferenceStatusPayload, PersistenceStatus, UIState } from '../../types/contracts'
import type {
  HealthCardModel,
  WorkspaceContextBandModel,
  WorkspaceOperatorDeckSectionModel,
  WorkspaceSpotlightModel,
} from '../../view-models/workbench'
import { buildHealthCards, formatEmptyStateLabel, summarizeDomainStates } from '../../view-models/workbench'

type Translate = (key: TranslationKey) => string

export type HealthDataItem = {
  id: string
  label: string
  value: string
}

export type ServiceHealthPanelModel = {
  band: WorkspaceContextBandModel
  cards: HealthCardModel[]
  updatedAtLabel: string
  requestIdLabel: string
  persistenceGroups: HealthDataItem[][]
}

export type HealthDiagnosticsModel = {
  summaryError?: AppError
  domainStatus: Record<string, UIState>
}

export function buildHealthDiagnosticsBandModel({
  t,
  summaryError,
  domainStatus,
}: {
  t: Translate
  summaryError?: AppError
  domainStatus: DomainStatusMap
}): WorkspaceContextBandModel {
  const entries = Object.entries(domainStatus)
  const degraded = entries.filter(([, value]) => value.state === 'degraded' || value.state === 'error')
  const latestRequestId =
    summaryError?.request_id ??
    degraded.map(([, value]) => value.request_id).find((value) => typeof value === 'string' && value.trim()) ??
    entries.map(([, value]) => value.request_id).find((value) => typeof value === 'string' && value.trim())

  return {
    eyebrow: t('workspace.health.requestIds'),
    title: summaryError?.code ?? (degraded.length > 0 ? t('workspace.overview.attention') : t('common.ready')),
    hint: summaryError?.message ?? t('workspace.health.requestIdsDescription'),
    accent: degraded.length > 0 || summaryError ? 'amber' : 'teal',
    items: [
      {
        id: 'degraded-count',
        label: t('workspace.overview.attention'),
        value: String(degraded.length),
        tone: degraded.length > 0 ? 'negative' : 'default',
      },
      {
        id: 'domains',
        label: t('workspace.nav'),
        value: String(entries.length),
      },
        {
          id: 'latest-request-id',
          label: t('health.requestId'),
          value: latestRequestId ?? formatEmptyStateLabel('request-id'),
        },
      {
        id: 'summary-state',
        label: t('workspace.health.title'),
        value: summaryError ? t('health.state.degraded') : t('health.state.ready'),
      },
    ],
  }
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
  const cards = buildHealthCards(domainStatus, t)
  const readyCount = cards.filter((card) => card.state === 'ready').length
  const attentionCount = cards.filter((card) => card.state === 'degraded' || card.state === 'error').length
  const latestRequestId =
    cards.map((card) => card.requestId).find((value) => typeof value === 'string' && value.trim()) ??
    formatEmptyStateLabel('request-id')
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
    band: {
      eyebrow: t('workspace.health.title'),
      title:
        attentionCount > 0
          ? `${attentionCount} ${t('workspace.overview.attention').toLowerCase()}`
          : `${readyCount} ${t('common.ready').toLowerCase()}`,
      hint: persistenceStatus?.status ?? t('workspace.health.operatorDeckDescription'),
      accent: attentionCount > 0 ? 'amber' : 'teal',
      items: [
        {
          id: 'ready',
          label: t('common.ready'),
          value: String(readyCount),
          tone: readyCount > 0 ? 'positive' : 'default',
        },
        {
          id: 'attention',
          label: t('workspace.overview.attention'),
          value: String(attentionCount),
          tone: attentionCount > 0 ? 'negative' : 'default',
        },
        {
          id: 'matching',
          label: t('strategy.matching'),
          value: persistenceStatus?.matching?.health?.status ?? t('common.disabled'),
        },
        {
          id: 'request',
          label: t('health.requestId'),
          value: latestRequestId,
        },
      ],
    },
    cards,
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

export function buildHealthContextBandModel({
  t,
  domainStatus,
  persistenceStatus,
  inferenceStatus,
}: {
  t: Translate
  domainStatus: DomainStatusMap
  persistenceStatus?: PersistenceStatus
  inferenceStatus?: InferenceStatusPayload
}): WorkspaceContextBandModel {
  const domainSummary = summarizeDomainStates(domainStatus)
  const matchingStatus = persistenceStatus?.matching?.health?.status ?? t('common.disabled')

  return {
    eyebrow: t('workspace.health.title'),
    title: persistenceStatus?.status ?? t('common.disabled'),
    hint: t('workspace.health.operatorDeckDescription'),
    accent: domainSummary.attentionCount > 0 ? 'amber' : 'teal',
    items: [
      {
        id: 'ready',
        label: t('common.ready'),
        value: String(domainSummary.readyCount),
        tone: domainSummary.readyCount > 0 ? 'positive' : 'default',
      },
      {
        id: 'attention',
        label: t('workspace.overview.attention'),
        value: String(domainSummary.attentionCount),
        tone: domainSummary.attentionCount > 0 ? 'negative' : 'default',
      },
      {
        id: 'matching',
        label: t('strategy.matching'),
        value: matchingStatus,
      },
      {
        id: 'rollout',
        label: t('workspace.inference.rolloutMode'),
        value: formatInferenceMode(t, inferenceStatus),
        tone:
          inferenceStatus?.rollout?.effective_mode === 'primary' || inferenceStatus?.mode === 'primary'
            ? 'accent'
            : 'default',
      },
      {
        id: 'ticks',
        label: t('strategy.ticksProcessed'),
        value: String(persistenceStatus?.worker.processed_ticks ?? 0),
      },
      {
        id: 'symbols',
        label: t('workspace.health.trackedSymbols'),
        value: String(persistenceStatus?.worker.tracked_symbols?.length ?? 0),
      },
    ],
  }
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
