import type { TranslationKey } from '../../i18n/messages'
import type { CoreFlowMap } from '../../store/slices/shared'
import type { OrderTimelineEvent, PersistenceStatus, TradingPolicy, UIState } from '../../types/contracts'
import { buildExecutionAnomalySummary, buildExecutionOrderReadModels } from './read-models'

const EXECUTION_PROGRESS_STEPS = ['precheck', 'submit', 'feedback', 'cancel'] as const

const EXECUTION_STEP_LABELS: Record<(typeof EXECUTION_PROGRESS_STEPS)[number], TranslationKey> = {
  precheck: 'execution.precheck',
  submit: 'execution.submit',
  feedback: 'flow.step.feedback',
  cancel: 'execution.cancel',
}

const FLOW_STATE_LABELS = {
  idle: 'health.state.idle',
  active: 'health.state.loading',
  success: 'health.state.ready',
  degraded: 'health.state.degraded',
  error: 'health.state.error',
} as const

type Translate = (key: TranslationKey) => string

export type ExecutionSummaryItem = {
  id: string
  label: string
  value: string
}

export type ExecutionProgressItem = {
  id: (typeof EXECUTION_PROGRESS_STEPS)[number]
  title: string
  state: CoreFlowMap[(typeof EXECUTION_PROGRESS_STEPS)[number]]['state']
  stateLabel: string
  reason: string
  requestId?: string
}

export type ExecutionOperationsPanelModel = {
  state: UIState['state']
  stateLabel: string
  summary: string
  anomalies: string[]
  items: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
  emptyTitle?: string
  emptyHint?: string
}

type BuildExecutionSummaryParams = {
  t: Translate
  broker: 'binance' | 'alpaca'
  selectedSymbol: string
  alpacaSymbol: string
  tradingPolicy?: TradingPolicy
  latestBid?: string
  latestAsk?: string
}

type BuildExecutionOperationsParams = {
  t: Translate
  selectedSymbol: string
  orderEvents: OrderTimelineEvent[]
  persistenceStatus?: PersistenceStatus
  domainStatus: UIState
}

function formatInteger(value?: number | null): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '—'
  }
  return String(value)
}

function normalizeOrderStatus(value?: string): string {
  return `${value ?? ''}`.trim().toLowerCase()
}

export function buildExecutionSummary({
  t,
  broker,
  selectedSymbol,
  alpacaSymbol,
  tradingPolicy,
  latestBid,
  latestAsk,
}: BuildExecutionSummaryParams): ExecutionSummaryItem[] {
  return [
    {
      id: 'symbol',
      label: 'Symbol',
      value: broker === 'binance' ? selectedSymbol : alpacaSymbol.toUpperCase(),
    },
    {
      id: 'policy',
      label: t('execution.policy'),
      value: tradingPolicy?.enforced ? t('common.ready') : t('common.disabled'),
    },
    {
      id: 'bid',
      label: t('market.bestBid'),
      value: latestBid ?? '—',
    },
    {
      id: 'ask',
      label: t('market.bestAsk'),
      value: latestAsk ?? '—',
    },
  ]
}

export function buildExecutionProgressItems(coreFlow: CoreFlowMap, t: Translate): ExecutionProgressItem[] {
  return EXECUTION_PROGRESS_STEPS.map((step) => {
    const item = coreFlow[step]
    return {
      id: step,
      title: t(EXECUTION_STEP_LABELS[step]),
      state: item.state,
      stateLabel: t(FLOW_STATE_LABELS[item.state]),
      reason: item.reason?.trim() ? item.reason : t('common.na'),
      requestId: item.request_id,
    }
  })
}

export function buildExecutionOperationsPanel({
  t,
  selectedSymbol,
  orderEvents,
  persistenceStatus,
  domainStatus,
}: BuildExecutionOperationsParams): ExecutionOperationsPanelModel {
  const filteredEvents = orderEvents.filter((item) => item.symbol === selectedSymbol)
  const orderModels = buildExecutionOrderReadModels(filteredEvents, selectedSymbol)
  const activeOrders = orderModels.filter((item) =>
    ['submit', 'accepted', 'partial_fill', 'cancel_requested'].includes(item.latestPhase),
  ).length
  const acceptedCount = orderModels.filter((item) => item.latestPhase === 'accepted').length
  const partialFillCount = orderModels.filter((item) => item.latestPhase === 'partial_fill').length
  const filledCount = orderModels.filter((item) => item.latestPhase === 'fill').length
  const rejectedCount = orderModels.filter((item) => item.latestPhase === 'rejected').length
  const canceledCount = orderModels.filter((item) => item.latestPhase === 'canceled').length
  const anomalySummary = buildExecutionAnomalySummary(orderModels)
  const latestAnomaly = orderModels.find((item) =>
    ['rejected', 'canceled'].includes(item.latestPhase),
  )
  const matchingStats = persistenceStatus?.matching?.stats
  const anomalies: string[] = []

  if (rejectedCount > 0) {
    anomalies.push(`${t('workspace.execution.operationsRejected')}: ${rejectedCount}`)
  }
  if (canceledCount > 0) {
    anomalies.push(`${t('workspace.execution.operationsCanceled')}: ${canceledCount}`)
  }
  if (anomalySummary.rejectionReasons[0]) {
    anomalies.push(
      `${t('workspace.execution.operationsLatestAnomaly')}: ${anomalySummary.rejectionReasons[0].reason} · ${anomalySummary.rejectionReasons[0].count}`,
    )
  }
  if (anomalySummary.cancelFailures > 0) {
    anomalies.push(`${t('workspace.execution.operationsCancelHoldbacks')}: ${anomalySummary.cancelFailures}`)
  }
  if (latestAnomaly?.latestStatus) {
    anomalies.push(
      `${t('workspace.execution.operationsLatestAnomaly')}: ${latestAnomaly.latestStatus} · ${latestAnomaly.requestId ?? '—'}`,
    )
  }

  if (filteredEvents.length === 0) {
    return {
      state: domainStatus.state,
      stateLabel: t(`health.state.${domainStatus.state}` as TranslationKey),
      summary: selectedSymbol,
      anomalies,
      items: [],
      emptyTitle: t('workspace.execution.operationsEmpty'),
      emptyHint: t('workspace.execution.operationsDescription'),
    }
  }

  return {
    state: domainStatus.state,
    stateLabel: t(`health.state.${domainStatus.state}` as TranslationKey),
    summary: `${selectedSymbol} · ${orderModels.length} ${t('workspace.execution.operationsSummarySuffix')}`,
    anomalies,
    items: [
      {
        id: 'observed',
        label: t('workspace.execution.operationsObserved'),
        value: String(orderModels.length),
      },
      {
        id: 'active',
        label: t('workspace.execution.operationsActive'),
        value: String(activeOrders),
        tone: activeOrders > 0 ? 'accent' : 'default',
      },
      {
        id: 'accepted',
        label: t('workspace.execution.operationsAccepted'),
        value: String(acceptedCount),
      },
      {
        id: 'partialFill',
        label: t('workspace.execution.operationsPartialFills'),
        value: String(partialFillCount),
      },
      {
        id: 'filled',
        label: t('workspace.execution.operationsFilled'),
        value: String(filledCount),
      },
      {
        id: 'rejected',
        label: t('workspace.execution.operationsRejected'),
        value: String(rejectedCount),
        tone: rejectedCount > 0 ? 'accent' : 'default',
      },
      {
        id: 'canceled',
        label: t('workspace.execution.operationsCanceled'),
        value: String(canceledCount),
        tone: canceledCount > 0 ? 'accent' : 'default',
      },
      {
        id: 'submitToAccepted',
        label: t('workspace.execution.operationsSubmitToAccepted'),
        value: formatInteger(anomalySummary.avgSubmitToAcceptedMs ? Math.round(anomalySummary.avgSubmitToAcceptedMs) : undefined),
      },
      {
        id: 'submitToFill',
        label: t('workspace.execution.operationsSubmitToFill'),
        value: formatInteger(anomalySummary.avgSubmitToFillMs ? Math.round(anomalySummary.avgSubmitToFillMs) : undefined),
      },
      {
        id: 'slippage',
        label: t('workspace.execution.operationsSlippage'),
        value: anomalySummary.fillSlippageBps !== undefined ? anomalySummary.fillSlippageBps.toFixed(1) : '—',
        tone: anomalySummary.fillSlippageBps !== undefined && Math.abs(anomalySummary.fillSlippageBps) > 5 ? 'accent' : 'default',
      },
      {
        id: 'matchingLive',
        label: t('workspace.execution.operationsMatchingLive'),
        value: formatInteger(matchingStats?.live_orders),
      },
      {
        id: 'tradeCount',
        label: t('workspace.execution.operationsTrades'),
        value: formatInteger(matchingStats?.trade_count),
      },
      {
        id: 'latestStatus',
        label: t('workspace.execution.operationsLatestStatus'),
        value: orderModels[0]?.latestStatus ?? orderModels[0]?.latestPhase ?? '—',
      },
    ],
  }
}
