import type { TranslationKey } from '../../i18n/messages'
import type { CoreFlowMap } from '../../store/slices/shared'
import type { BinanceRule, PersistenceStatus, TradingPolicy, UIState } from '../../types/contracts'
import { formatDerivedPrice, parseNumericString, type PreparedTradingSnapshot, type WorkspaceSpotlightModel } from '../../view-models/workbench'
import { type PreparedExecutionSelection } from './read-models'

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

type BuildExecutionSpotlightParams = {
  t: Translate
  snapshot: PreparedTradingSnapshot
  preparedSelection: PreparedExecutionSelection
  tradingPolicy?: TradingPolicy
  binanceRule?: BinanceRule
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
  preparedSelection: PreparedExecutionSelection
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

export function buildExecutionSpotlightModel({
  t,
  snapshot,
  preparedSelection,
  tradingPolicy,
  binanceRule,
}: BuildExecutionSpotlightParams): WorkspaceSpotlightModel {
  const latestLifecycle = preparedSelection.latestOrder?.latestStatus ?? preparedSelection.latestOrder?.latestPhase ?? '—'

  return {
    summary: t('workspace.execution.linkageHint').replace('{symbol}', snapshot.selectedSymbol),
    hint: t('workspace.execution.linkageDetail'),
    chips: [
      snapshot.selectedSymbol,
      snapshot.signalValue,
      tradingPolicy?.enforced ? t('common.ready') : t('common.disabled'),
      binanceRule ? t('common.ready') : t('workspace.execution.lifecycleWaitingRule'),
    ],
    metrics: [
      {
        id: 'mid-price',
        label: t('orderbook.midPrice'),
        value: snapshot.midPriceValue,
        tone: 'accent',
        hint: `${t('common.updatedAt')}: ${snapshot.quoteUpdatedAtValue}`,
      },
      {
        id: 'spread',
        label: t('orderbook.spread'),
        value: snapshot.spreadValue,
      },
      {
        id: 'active-orders',
        label: t('workspace.execution.operationsActive'),
        value: String(preparedSelection.activeOrderCount),
        tone: preparedSelection.activeOrderCount > 0 ? 'accent' : 'default',
      },
      {
        id: 'latest-lifecycle',
        label: t('workspace.execution.lifecycleLatest'),
        value: latestLifecycle,
        hint: preparedSelection.latestOrder?.requestId ?? t('common.na'),
      },
    ],
  }
}

export function buildExecutionDeskSpotlightModel({
  t,
  broker,
  selectedSymbol,
  alpacaSymbol,
  tradingPolicy,
  latestBid,
  latestAsk,
  binanceRule,
}: {
  t: Translate
  broker: 'binance' | 'alpaca'
  selectedSymbol: string
  alpacaSymbol: string
  tradingPolicy?: TradingPolicy
  latestBid?: string
  latestAsk?: string
  binanceRule?: BinanceRule
}): WorkspaceSpotlightModel {
  const symbol = broker === 'binance' ? selectedSymbol : alpacaSymbol.toUpperCase()
  const bid = parseNumericString(latestBid)
  const ask = parseNumericString(latestAsk)
  const spread = bid !== undefined && ask !== undefined ? ask - bid : undefined

  return {
    summary: broker === 'binance' ? t('execution.binanceTest') : t('execution.alpacaPaper'),
    hint: symbol,
    chips: [
      symbol,
      tradingPolicy?.enforced ? t('common.ready') : t('common.disabled'),
      broker === 'binance' && binanceRule ? t('common.ready') : broker === 'binance' ? t('workspace.execution.lifecycleWaitingRule') : 'Paper',
    ],
    metrics: [
      {
        id: 'best-bid',
        label: t('market.bestBid'),
        value: latestBid ?? '—',
        tone: 'positive',
      },
      {
        id: 'best-ask',
        label: t('market.bestAsk'),
        value: latestAsk ?? '—',
        tone: 'negative',
      },
      {
        id: 'spread',
        label: t('orderbook.spread'),
        value: formatDerivedPrice(spread),
      },
      {
        id: 'policy',
        label: t('execution.policy'),
        value: tradingPolicy?.enforced ? t('common.ready') : t('common.disabled'),
        hint:
          broker === 'binance'
            ? `${t('execution.submit')}: ${binanceRule?.symbol ?? symbol}`
            : t('execution.accountSnapshot'),
      },
    ],
  }
}

export function buildExecutionOperationsPanel({
  t,
  selectedSymbol,
  preparedSelection,
  persistenceStatus,
  domainStatus,
}: BuildExecutionOperationsParams): ExecutionOperationsPanelModel {
  const {
    orderModels,
    activeOrderCount,
    acceptedCount,
    partialFillCount,
    filledCount,
    rejectedCount,
    canceledCount,
    lifecycleDistribution,
    accountSummary,
    latestAnomaly,
    diagnosisState,
    diagnosisReason,
    latestOrder,
    anomalySummary,
  } = preparedSelection
  const orderCount = orderModels.length
  const {
    rejectionReasons,
    cancelFailureReasons,
    cancelFailures,
    avgSubmitToAcceptedMs,
    avgSubmitToFillMs,
    fillSlippageBps,
    partialFillRatio,
  } = anomalySummary
  const matchingStats = persistenceStatus?.matching?.stats
  const anomalies: string[] = []

  if (rejectedCount > 0) {
    anomalies.push(`${t('workspace.execution.operationsRejected')}: ${rejectedCount}`)
  }
  if (canceledCount > 0) {
    anomalies.push(`${t('workspace.execution.operationsCanceled')}: ${canceledCount}`)
  }
  if (rejectionReasons[0]) {
    anomalies.push(
      `${t('workspace.execution.operationsLatestAnomaly')}: ${rejectionReasons[0].reason} · ${rejectionReasons[0].count}`,
    )
  }
  if (cancelFailures > 0) {
    anomalies.push(`${t('workspace.execution.operationsCancelHoldbacks')}: ${cancelFailures}`)
  }
  if (cancelFailureReasons[0]) {
    anomalies.push(
      `${t('workspace.execution.operationsCancelFailureReason')}: ${cancelFailureReasons[0].reason} · ${cancelFailureReasons[0].count}`,
    )
  }
  if (latestAnomaly?.latestStatus) {
    anomalies.push(
      `${t('workspace.execution.operationsLatestAnomaly')}: ${latestAnomaly.latestStatus} · ${latestAnomaly.requestId ?? '—'}`,
    )
  }
  if (fillSlippageBps !== undefined && Math.abs(fillSlippageBps) > 5) {
    anomalies.push(
      `${t('workspace.execution.operationsSlippage')}: ${fillSlippageBps.toFixed(1)} bps`,
    )
  }
  if (avgSubmitToAcceptedMs !== undefined && avgSubmitToAcceptedMs > 10_000) {
    anomalies.push(
      `${t('workspace.execution.operationsSubmitToAccepted')}: ${Math.round(avgSubmitToAcceptedMs)} ms`,
    )
  }

  if (orderCount === 0) {
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
    diagnosisState === 'hold'
      ? {
          label: t('workspace.execution.diagnosisHold'),
          tone: 'danger' as const,
          hint: diagnosisReason ?? t('workspace.execution.diagnosisHintHold'),
        }
      : diagnosisState === 'caution-pending'
        ? {
            label: t('workspace.execution.diagnosisCaution'),
            tone: 'accent' as const,
            hint: t('workspace.execution.diagnosisHintPending'),
          }
        : diagnosisState === 'caution-anomaly'
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
    summary: `${selectedSymbol} · ${orderCount} ${t('workspace.execution.operationsSummarySuffix')}`,
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
      ...rejectionReasons.map((item) => ({
        id: `reject-${item.reason}`,
        label: t('workspace.execution.reasonDistributionRejected'),
        value: `${item.reason} · ${item.count}`,
        tone: 'accent' as const,
      })),
      ...cancelFailureReasons.map((item) => ({
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
        value: String(orderCount),
      },
      {
        id: 'active',
        label: t('workspace.execution.operationsActive'),
        value: String(activeOrderCount),
        tone: activeOrderCount > 0 ? 'accent' : 'default',
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
        value: formatInteger(avgSubmitToAcceptedMs ? Math.round(avgSubmitToAcceptedMs) : undefined),
      },
      {
        id: 'submitToFill',
        label: t('workspace.execution.operationsSubmitToFill'),
        value: formatInteger(avgSubmitToFillMs ? Math.round(avgSubmitToFillMs) : undefined),
      },
      {
        id: 'partialFillRatio',
        label: t('workspace.execution.operationsPartialFillRatio'),
        value: formatPercent(partialFillRatio),
      },
      {
        id: 'slippage',
        label: t('workspace.execution.operationsSlippage'),
        value: fillSlippageBps !== undefined ? fillSlippageBps.toFixed(1) : '—',
        tone: fillSlippageBps !== undefined && Math.abs(fillSlippageBps) > 5 ? 'accent' : 'default',
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
        value: latestOrder?.latestStatus ?? latestOrder?.latestPhase ?? '—',
      },
    ],
  }
}
