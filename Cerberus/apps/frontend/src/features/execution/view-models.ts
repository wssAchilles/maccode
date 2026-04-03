import type { TranslationKey } from '../../i18n/messages'
import type { CoreFlowMap } from '../../store/slices/shared'
import type { BinanceRule, PersistenceStatus, TradingPolicy, UIState } from '../../types/contracts'
import {
  formatDateTimeLabel,
  formatDerivedPrice,
  formatEmptyStateLabel,
  parseNumericString,
  type PreparedTradingSnapshot,
  type WorkspaceContextBandModel,
  type WorkspaceOperatorDeckSectionModel,
  type WorkspaceSpotlightModel,
} from '../../view-models/workbench'
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
  band: WorkspaceContextBandModel
  anomalies: string[]
  diagnosisLabel: string
  diagnosisTone: 'default' | 'accent' | 'danger'
  diagnosisHint: string
  headlineItems: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
  latencyItems: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
  venueItems: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
  lifecycleSummary: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
  reasonSummary: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
  accountSummary: { id: string; label: string; value: string; tone?: 'default' | 'muted' | 'accent' }[]
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
  binanceRule?: BinanceRule
  alpacaAccountLabel?: string
}

type BuildExecutionOperatorSectionsParams = {
  t: Translate
  snapshot: PreparedTradingSnapshot
  preparedSelection: PreparedExecutionSelection
  tradingPolicy?: TradingPolicy
  binanceRule?: BinanceRule
}

type BuildExecutionHeroBandParams = {
  t: Translate
  snapshot: PreparedTradingSnapshot
  preparedSelection: PreparedExecutionSelection
  tradingPolicy?: TradingPolicy
  binanceRule?: BinanceRule
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
    return formatEmptyStateLabel('generic')
  }
  return String(value)
}

function formatPercent(value?: number | null): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return formatEmptyStateLabel('generic')
  }
  return `${(value * 100).toFixed(1)}%`
}

export function buildExecutionDeskSections({
  t,
  broker,
  selectedSymbol,
  alpacaSymbol,
  tradingPolicy,
  latestBid,
  latestAsk,
  binanceRule,
  alpacaAccountLabel,
}: BuildExecutionSummaryParams): WorkspaceOperatorDeckSectionModel[] {
  const symbol = broker === 'binance' ? selectedSymbol : alpacaSymbol.toUpperCase()
  const bid = parseNumericString(latestBid)
  const ask = parseNumericString(latestAsk)
  const spread = bid !== undefined && ask !== undefined ? ask - bid : undefined

  const routeItems = [
    {
      id: 'venue',
      label: t('workspace.execution.operatorVenue'),
      value: broker === 'binance' ? 'Binance Testnet' : 'Alpaca Paper',
      tone: 'accent' as const,
    },
    {
      id: 'symbol',
      label: 'Symbol',
      value: symbol,
    },
    {
      id: 'best-bid',
      label: t('market.bestBid'),
      value: latestBid ?? formatEmptyStateLabel('bid'),
      tone: 'positive' as const,
    },
    {
      id: 'best-ask',
      label: t('market.bestAsk'),
      value: latestAsk ?? formatEmptyStateLabel('ask'),
      tone: 'negative' as const,
    },
    {
      id: 'spread',
      label: t('orderbook.spread'),
      value: formatDerivedPrice(spread),
    },
  ]

  const guardrailItems =
    broker === 'binance'
      ? [
          {
            id: 'policy',
            label: t('execution.policy'),
            value: tradingPolicy?.enforced ? t('common.ready') : t('common.disabled'),
          },
          {
            id: 'max-qty',
            label: t('workspace.execution.operatorMaxQty'),
            value:
              tradingPolicy?.max_binance_order_qty !== undefined && tradingPolicy?.max_binance_order_qty !== null
                ? String(tradingPolicy.max_binance_order_qty)
                : formatEmptyStateLabel('generic'),
          },
          {
            id: 'max-notional',
            label: t('workspace.execution.operatorMaxNotional'),
            value:
              tradingPolicy?.max_binance_order_notional_usd !== undefined &&
              tradingPolicy?.max_binance_order_notional_usd !== null
                ? formatDerivedPrice(tradingPolicy.max_binance_order_notional_usd, 2)
                : formatEmptyStateLabel('generic'),
          },
          {
            id: 'min-qty',
            label: t('workspace.execution.operatorMinQty'),
            value:
              binanceRule?.min_qty !== undefined && binanceRule?.min_qty !== null
                ? formatDerivedPrice(binanceRule.min_qty)
                : formatEmptyStateLabel('generic'),
          },
          {
            id: 'min-notional',
            label: t('workspace.execution.operatorMinNotional'),
            value:
              binanceRule?.min_notional !== undefined && binanceRule?.min_notional !== null
                ? formatDerivedPrice(binanceRule.min_notional, 2)
                : formatEmptyStateLabel('generic'),
          },
        ]
      : [
          {
            id: 'policy',
            label: t('execution.policy'),
            value: tradingPolicy?.enforced ? t('common.ready') : t('common.disabled'),
          },
          {
            id: 'max-qty',
            label: t('workspace.execution.operatorMaxQty'),
            value:
              tradingPolicy?.max_alpaca_order_qty !== undefined && tradingPolicy?.max_alpaca_order_qty !== null
                ? String(tradingPolicy.max_alpaca_order_qty)
                : formatEmptyStateLabel('generic'),
          },
          {
            id: 'max-notional',
            label: t('workspace.execution.operatorMaxNotional'),
            value:
              tradingPolicy?.max_alpaca_limit_notional_usd !== undefined &&
              tradingPolicy?.max_alpaca_limit_notional_usd !== null
                ? formatDerivedPrice(tradingPolicy.max_alpaca_limit_notional_usd, 2)
                : formatEmptyStateLabel('generic'),
          },
          {
            id: 'account',
            label: t('workspace.execution.operatorAccount'),
            value: alpacaAccountLabel ?? formatEmptyStateLabel('generic'),
          },
        ]

  return [
    {
      id: 'route',
      title: t('workspace.execution.operatorRouteTitle'),
      summary: t('workspace.execution.operatorRouteDescription'),
      accent: 'cyan',
      postureLabel: symbol,
      visualPriority: 'hero',
      items: routeItems,
    },
    {
      id: 'guardrails',
      title: t('workspace.execution.operatorGuardrailsTitle'),
      summary: t('workspace.execution.operatorGuardrailsDescription'),
      accent: 'amber',
      postureLabel: tradingPolicy?.enforced ? t('common.ready') : t('common.disabled'),
      items: guardrailItems,
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
  const latestLifecycle =
    preparedSelection.latestOrder?.latestStatus ??
    preparedSelection.latestOrder?.latestPhase ??
    t('execution.noLifecycle')

  return {
    summary: t('workspace.execution.linkageHint').replace('{symbol}', snapshot.selectedSymbol),
    hint: t('workspace.execution.linkageDetail'),
    chips: [
      snapshot.selectedSymbol,
      snapshot.signalValue,
      tradingPolicy?.enforced ? t('common.ready') : t('common.disabled'),
      binanceRule ? t('common.ready') : t('workspace.execution.lifecycleWaitingRule'),
    ],
    accent: preparedSelection.activeOrderCount > 0 ? 'amber' : 'cyan',
    postureLabel: latestLifecycle,
    metrics: [
      {
        id: 'mid-price',
        label: t('orderbook.midPrice'),
        value: snapshot.midPriceValue,
        tone: 'accent',
        hint: `${t('common.updatedAt')}: ${snapshot.quoteUpdatedAtValue}`,
        visualPriority: 'primary',
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
    accent: broker === 'binance' ? 'amber' : 'cyan',
    postureLabel: broker === 'binance' ? 'Binance' : 'Alpaca',
    metrics: [
      {
        id: 'best-bid',
        label: t('market.bestBid'),
        value: latestBid ?? formatEmptyStateLabel('bid'),
        tone: 'positive',
      },
      {
        id: 'best-ask',
        label: t('market.bestAsk'),
        value: latestAsk ?? formatEmptyStateLabel('ask'),
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

export function buildExecutionDeskContextModel({
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
}): WorkspaceContextBandModel {
  const symbol = broker === 'binance' ? selectedSymbol : alpacaSymbol.toUpperCase()
  const bid = parseNumericString(latestBid)
  const ask = parseNumericString(latestAsk)
  const spread = bid !== undefined && ask !== undefined ? ask - bid : undefined

  return {
    eyebrow: broker === 'binance' ? t('execution.binanceTest') : t('execution.alpacaPaper'),
    title: symbol,
    hint:
      broker === 'binance'
        ? tradingPolicy?.enforced
          ? t('workspace.execution.operatorGuardrailsDescription')
          : t('workspace.execution.lifecycleWaitingRule')
        : t('execution.accountSnapshot'),
    items: [
      {
        id: 'venue',
        label: t('workspace.execution.operatorVenue'),
        value: broker === 'binance' ? 'Binance Testnet' : 'Alpaca Paper',
        tone: 'accent',
      },
      {
        id: 'bid',
        label: t('market.bestBid'),
        value: latestBid ?? formatEmptyStateLabel('bid'),
        tone: 'positive',
      },
      {
        id: 'ask',
        label: t('market.bestAsk'),
        value: latestAsk ?? formatEmptyStateLabel('ask'),
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
        tone: tradingPolicy?.enforced ? 'accent' : 'default',
      },
      {
        id: 'rule',
        label: t('workspace.execution.operatorGuardrailsTitle'),
        value: broker === 'binance' ? (binanceRule ? t('common.ready') : t('workspace.execution.lifecycleWaitingRule')) : 'Paper',
      },
    ],
  }
}

export function buildExecutionHeroBandModel({
  t,
  snapshot,
  preparedSelection,
  tradingPolicy,
  binanceRule,
}: BuildExecutionHeroBandParams): WorkspaceContextBandModel {
  const latestLifecycle =
    preparedSelection.latestOrder?.latestStatus ??
    preparedSelection.latestOrder?.latestPhase ??
    t('execution.noLifecycle')

  return {
    eyebrow: t('workspace.execution.description'),
    title: snapshot.selectedSymbol,
    hint: snapshot.feedbackValue ?? t('common.heartbeat'),
    accent: preparedSelection.activeOrderCount > 0 ? 'amber' : 'cyan',
    items: [
      {
        id: 'signal',
        label: t('strategy.signal'),
        value: snapshot.signalValue,
        tone: 'accent',
      },
      {
        id: 'best-bid',
        label: t('market.bestBid'),
        value: snapshot.bestBidValue,
        tone: 'positive',
      },
      {
        id: 'best-ask',
        label: t('market.bestAsk'),
        value: snapshot.bestAskValue,
        tone: 'negative',
      },
      {
        id: 'active-orders',
        label: t('workspace.execution.operationsActive'),
        value: String(preparedSelection.activeOrderCount),
        tone: preparedSelection.activeOrderCount > 0 ? 'accent' : 'default',
      },
      {
        id: 'latest-lifecycle',
        label: t('workspace.execution.operationsLatestStatus'),
        value: latestLifecycle,
      },
      {
        id: 'guardrail-state',
        label: t('workspace.execution.operatorGuardrailsTitle'),
        value: tradingPolicy?.enforced
          ? binanceRule
            ? t('common.ready')
            : t('workspace.execution.lifecycleWaitingRule')
          : t('common.disabled'),
        tone: tradingPolicy?.enforced ? 'accent' : 'default',
      },
    ],
  }
}

export function buildExecutionInspectorBandModel({
  t,
  snapshot,
  preparedSelection,
  orderbookPanel,
}: {
  t: Translate
  snapshot: PreparedTradingSnapshot
  preparedSelection: PreparedExecutionSelection
  orderbookPanel: {
    totalDepthLabel: string
    updatedAtLabel: string
    liquidityBiasLabel: string
  }
}): WorkspaceContextBandModel {
  const latestLifecycle =
    preparedSelection.latestOrder?.latestStatus ??
    preparedSelection.latestOrder?.latestPhase ??
    t('execution.noLifecycle')

  return {
    eyebrow: t('workspace.execution.title'),
    title: snapshot.selectedSymbol,
    hint: orderbookPanel.liquidityBiasLabel,
    accent: preparedSelection.activeOrderCount > 0 ? 'amber' : 'cyan',
    items: [
      {
        id: 'signal',
        label: t('strategy.signal'),
        value: snapshot.signalValue,
        tone: 'accent',
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
      },
      {
        id: 'mid-price',
        label: t('orderbook.midPrice'),
        value: snapshot.midPriceValue,
        tone: 'accent',
      },
      {
        id: 'total-depth',
        label: t('orderbook.totalDepth'),
        value: orderbookPanel.totalDepthLabel,
      },
      {
        id: 'updated-at',
        label: t('common.updatedAt'),
        value: orderbookPanel.updatedAtLabel,
      },
    ],
  }
}

export function buildExecutionOperatorSections({
  t,
  snapshot,
  preparedSelection,
  tradingPolicy,
  binanceRule,
}: BuildExecutionOperatorSectionsParams): WorkspaceOperatorDeckSectionModel[] {
  const latestLifecycle =
    preparedSelection.latestOrder?.latestStatus ??
    preparedSelection.latestOrder?.latestPhase ??
    t('execution.noLifecycle')

  return [
    {
      id: 'execution-posture',
      title: t('workspace.execution.operatorFlowTitle'),
      summary: t('workspace.execution.operatorFlowDescription'),
      accent: preparedSelection.activeOrderCount > 0 ? 'amber' : 'cyan',
      postureLabel: latestLifecycle,
      visualPriority: 'hero',
      items: [
        {
          id: 'symbol',
          label: 'Symbol',
          value: snapshot.selectedSymbol,
          tone: 'accent',
        },
        {
          id: 'signal',
          label: t('strategy.signal'),
          value: snapshot.signalValue,
          tone: 'accent',
        },
        {
          id: 'active-orders',
          label: t('workspace.execution.operationsActive'),
          value: String(preparedSelection.activeOrderCount),
        },
        {
          id: 'latest-lifecycle',
          label: t('workspace.execution.lifecycleLatest'),
          value: latestLifecycle,
        },
        {
          id: 'feedback-updated-at',
          label: t('common.updatedAt'),
          value: snapshot.feedbackAtValue,
        },
      ],
    },
    {
      id: 'execution-venue',
      title: t('workspace.execution.operatorVenueTitle'),
      summary: t('workspace.execution.operatorVenueDescription'),
      accent: binanceRule ? 'teal' : 'amber',
      postureLabel: tradingPolicy?.enforced ? t('common.ready') : t('common.disabled'),
      items: [
        {
          id: 'policy',
          label: t('execution.policy'),
          value: tradingPolicy?.enforced ? t('common.ready') : t('common.disabled'),
        },
        {
          id: 'venue-rule',
          label: t('workspace.execution.lifecycleVenueRule'),
          value: binanceRule?.symbol ?? t('workspace.execution.lifecycleWaitingRule'),
        },
        {
          id: 'rule-updated-at',
          label: t('common.updatedAt'),
          value: formatDateTimeLabel(binanceRule?.refreshed_at),
        },
        {
          id: 'filled-count',
          label: t('workspace.execution.operationsFilled'),
          value: String(preparedSelection.filledCount),
          tone: preparedSelection.filledCount > 0 ? 'positive' : 'default',
        },
        {
          id: 'rejected-count',
          label: t('workspace.execution.operationsRejected'),
          value: String(preparedSelection.rejectedCount),
          tone: preparedSelection.rejectedCount > 0 ? 'negative' : 'default',
        },
      ],
    },
  ]
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
      `${t('workspace.execution.operationsLatestAnomaly')}: ${latestAnomaly.latestStatus} · ${latestAnomaly.requestId ?? formatEmptyStateLabel('request-id')}`,
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
    const band: WorkspaceContextBandModel = {
      eyebrow: t('workspace.execution.operationsTitle'),
      title: `${selectedSymbol} · ${t('workspace.execution.diagnosisUnavailable')}`,
      hint: t('workspace.execution.operationsDescription'),
      accent: 'cyan',
      items: [
        {
          id: 'observed',
          label: t('workspace.execution.operationsObserved'),
          value: '0',
        },
        {
          id: 'active',
          label: t('workspace.execution.operationsActive'),
          value: '0',
        },
        {
          id: 'latest-status',
          label: t('workspace.execution.operationsLatestStatus'),
          value: t('execution.noLifecycle'),
        },
        {
          id: 'matching-live',
          label: t('workspace.execution.operationsMatchingLive'),
          value: formatInteger(matchingStats?.live_orders),
        },
      ],
    }

    return {
      state: domainStatus.state,
      stateLabel: t(`health.state.${domainStatus.state}` as TranslationKey),
      summary: selectedSymbol,
      band,
      anomalies,
      diagnosisLabel: t('workspace.execution.diagnosisUnavailable'),
      diagnosisTone: 'default',
      diagnosisHint: t('workspace.execution.operationsDescription'),
      headlineItems: [],
      latencyItems: [],
      venueItems: [],
      lifecycleSummary: [],
      reasonSummary: [],
      accountSummary: [],
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

  const band: WorkspaceContextBandModel = {
    eyebrow: t('workspace.execution.operationsTitle'),
    title: `${selectedSymbol} · ${diagnosis.label}`,
    hint: diagnosis.hint,
    accent: diagnosis.tone === 'danger' ? 'amber' : diagnosis.tone === 'accent' ? 'cyan' : 'teal',
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
        id: 'latest-status',
        label: t('workspace.execution.operationsLatestStatus'),
        value: latestOrder?.latestStatus ?? latestOrder?.latestPhase ?? t('execution.noLifecycle'),
      },
      {
        id: 'latency',
        label: t('workspace.execution.operationsSubmitToAccepted'),
        value:
          avgSubmitToAcceptedMs !== undefined
            ? formatInteger(Math.round(avgSubmitToAcceptedMs))
            : t('execution.noLatencySample'),
        tone: avgSubmitToAcceptedMs !== undefined && avgSubmitToAcceptedMs > 10_000 ? 'negative' : 'default',
      },
    ],
  }

  return {
    state: domainStatus.state,
    stateLabel: t(`health.state.${domainStatus.state}` as TranslationKey),
    summary: `${selectedSymbol} · ${orderCount} ${t('workspace.execution.operationsSummarySuffix')}`,
    band,
    anomalies,
    diagnosisLabel: diagnosis.label,
    diagnosisTone: diagnosis.tone,
    diagnosisHint: diagnosis.hint,
    headlineItems: [
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
    ],
    latencyItems: [
      {
        id: 'submitToAccepted',
        label: t('workspace.execution.operationsSubmitToAccepted'),
        value:
          avgSubmitToAcceptedMs !== undefined
            ? formatInteger(Math.round(avgSubmitToAcceptedMs))
            : t('execution.noLatencySample'),
      },
      {
        id: 'submitToFill',
        label: t('workspace.execution.operationsSubmitToFill'),
        value:
          avgSubmitToFillMs !== undefined
            ? formatInteger(Math.round(avgSubmitToFillMs))
            : t('execution.noLatencySample'),
      },
      {
        id: 'partialFillRatio',
        label: t('workspace.execution.operationsPartialFillRatio'),
        value: formatPercent(partialFillRatio),
      },
      {
        id: 'slippage',
        label: t('workspace.execution.operationsSlippage'),
        value: fillSlippageBps !== undefined ? fillSlippageBps.toFixed(1) : t('execution.noLatencySample'),
        tone: fillSlippageBps !== undefined && Math.abs(fillSlippageBps) > 5 ? 'accent' : 'default',
      },
    ],
    venueItems: [
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
        value: latestOrder?.latestStatus ?? latestOrder?.latestPhase ?? t('execution.noLifecycle'),
      },
    ],
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
  }
}
