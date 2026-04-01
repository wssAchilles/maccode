import type { TranslationKey } from '../../i18n/messages'
import type { CoreFlowMap } from '../../store/slices/shared'
import type { OrderTimelineEvent, PersistenceStatus, TradingPolicy, UIState } from '../../types/contracts'
import {
  buildExecutionAccountSummaries,
  buildExecutionAnomalySummary,
  buildExecutionLifecycleDistribution,
  buildExecutionOrderReadModels,
} from './read-models'

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
  diagnosisLabel: string
  diagnosisTone: 'default' | 'accent' | 'danger'
  diagnosisHint: string
  lifecycleSummary: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
  reasonSummary: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
  accountSummary: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
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

function formatPercent(value?: number | null): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '—'
  }
  return `${(value * 100).toFixed(1)}%`
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
  const orderModels = buildExecutionOrderReadModels(orderEvents, selectedSymbol)
  const activeOrders = orderModels.filter((item) =>
    ['submit', 'accepted', 'partial_fill', 'cancel_requested'].includes(item.latestPhase),
  ).length
  const acceptedCount = orderModels.filter((item) => item.latestPhase === 'accepted').length
  const partialFillCount = orderModels.filter((item) => item.latestPhase === 'partial_fill').length
  const filledCount = orderModels.filter((item) => item.latestPhase === 'fill').length
  const rejectedCount = orderModels.filter((item) => item.latestPhase === 'rejected').length
  const canceledCount = orderModels.filter((item) => item.latestPhase === 'canceled').length
  const anomalySummary = buildExecutionAnomalySummary(orderModels)
  const lifecycleDistribution = buildExecutionLifecycleDistribution(orderModels)
  const accountSummary = buildExecutionAccountSummaries(orderModels)
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
  if (anomalySummary.cancelFailureReasons[0]) {
    anomalies.push(
      `${t('workspace.execution.operationsCancelFailureReason')}: ${anomalySummary.cancelFailureReasons[0].reason} · ${anomalySummary.cancelFailureReasons[0].count}`,
    )
  }
  if (latestAnomaly?.latestStatus) {
    anomalies.push(
      `${t('workspace.execution.operationsLatestAnomaly')}: ${latestAnomaly.latestStatus} · ${latestAnomaly.requestId ?? '—'}`,
    )
  }
  if (anomalySummary.fillSlippageBps !== undefined && Math.abs(anomalySummary.fillSlippageBps) > 5) {
    anomalies.push(
      `${t('workspace.execution.operationsSlippage')}: ${anomalySummary.fillSlippageBps.toFixed(1)} bps`,
    )
  }
  if (anomalySummary.avgSubmitToAcceptedMs !== undefined && anomalySummary.avgSubmitToAcceptedMs > 10_000) {
    anomalies.push(
      `${t('workspace.execution.operationsSubmitToAccepted')}: ${Math.round(anomalySummary.avgSubmitToAcceptedMs)} ms`,
    )
  }

  if (orderModels.length === 0) {
    return {
      state: domainStatus.state,
      stateLabel: t(`health.state.${domainStatus.state}` as TranslationKey),
      summary: selectedSymbol,
      anomalies,
      diagnosisLabel: t('workspace.execution.diagnosisUnavailable'),
      diagnosisTone: 'default',
      diagnosisHint: t('workspace.execution.operationsDescription'),
      lifecycleSummary: [],
      reasonSummary: [],
      accountSummary: [],
      items: [],
      emptyTitle: t('workspace.execution.operationsEmpty'),
      emptyHint: t('workspace.execution.operationsDescription'),
    }
  }

  const diagnosis =
    rejectedCount > 0 || anomalySummary.cancelFailures > 0
      ? {
          label: t('workspace.execution.diagnosisHold'),
          tone: 'danger' as const,
          hint:
            latestAnomaly?.latestReason ??
            anomalySummary.rejectionReasons[0]?.reason ??
            t('workspace.execution.diagnosisHintHold'),
        }
      : activeOrders > 0 && filledCount === 0 && partialFillCount === 0
        ? {
            label: t('workspace.execution.diagnosisCaution'),
            tone: 'accent' as const,
            hint: t('workspace.execution.diagnosisHintPending'),
          }
      : partialFillCount > 0 ||
          (anomalySummary.fillSlippageBps !== undefined && Math.abs(anomalySummary.fillSlippageBps) > 5)
        ? {
            label: t('workspace.execution.diagnosisCaution'),
            tone: 'accent' as const,
            hint: t('workspace.execution.diagnosisHintCaution'),
          }
        : {
            label: t('workspace.execution.diagnosisReady'),
            tone: 'accent' as const,
            hint: t('workspace.execution.diagnosisHintReady'),
          }

  return {
    state: domainStatus.state,
    stateLabel: t(`health.state.${domainStatus.state}` as TranslationKey),
    summary: `${selectedSymbol} · ${orderModels.length} ${t('workspace.execution.operationsSummarySuffix')}`,
    anomalies,
    diagnosisLabel: diagnosis.label,
    diagnosisTone: diagnosis.tone,
    diagnosisHint: diagnosis.hint,
    lifecycleSummary: [
      {
        id: 'submit',
        label: t('workspace.execution.lifecycleStatus.submitted'),
        value: String(lifecycleDistribution.submit),
      },
      {
        id: 'accepted',
        label: t('workspace.execution.operationsAccepted'),
        value: String(lifecycleDistribution.accepted),
        tone: lifecycleDistribution.accepted > 0 ? 'accent' : 'default',
      },
      {
        id: 'partialFill',
        label: t('workspace.execution.lifecycleStatus.partialFill'),
        value: String(lifecycleDistribution.partial_fill),
        tone: lifecycleDistribution.partial_fill > 0 ? 'accent' : 'default',
      },
      {
        id: 'fill',
        label: t('workspace.execution.lifecycleStatus.filled'),
        value: String(lifecycleDistribution.fill),
        tone: lifecycleDistribution.fill > 0 ? 'accent' : 'default',
      },
      {
        id: 'rejected',
        label: t('workspace.execution.lifecycleStatus.rejected'),
        value: String(lifecycleDistribution.rejected),
        tone: lifecycleDistribution.rejected > 0 ? 'accent' : 'default',
      },
      {
        id: 'cancelRequested',
        label: t('workspace.execution.lifecycleStatus.cancelRequested'),
        value: String(lifecycleDistribution.cancel_requested),
      },
      {
        id: 'canceled',
        label: t('workspace.execution.lifecycleStatus.canceled'),
        value: String(lifecycleDistribution.canceled),
      },
    ],
    reasonSummary: [
      ...anomalySummary.rejectionReasons.map((item) => ({
        id: `reject-${item.reason}`,
        label: t('workspace.execution.reasonDistributionRejected'),
        value: `${item.reason} · ${item.count}`,
        tone: 'accent' as const,
      })),
      ...anomalySummary.cancelFailureReasons.map((item) => ({
        id: `cancel-${item.reason}`,
        label: t('workspace.execution.reasonDistributionCanceled'),
        value: `${item.reason} · ${item.count}`,
        tone: 'accent' as const,
      })),
    ],
    accountSummary: accountSummary.slice(0, 3).map((item) => ({
      id: item.accountId,
      label: item.accountId,
      value: `${item.observed} ${t('workspace.execution.accountObservedShort')} · ${item.accepted} ${t('workspace.execution.accountAcceptedShort')} · ${item.partialFill} ${t('workspace.execution.accountPartialShort')} · ${item.filled} ${t('workspace.execution.accountFilledShort')}`,
      tone: item.rejected > 0 || item.canceled > 0 ? 'accent' : item.active > 0 ? 'accent' : 'default',
    })),
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
        id: 'partialFillRatio',
        label: t('workspace.execution.operationsPartialFillRatio'),
        value: formatPercent(anomalySummary.partialFillRatio),
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
