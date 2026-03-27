import type { TranslationKey } from '../../i18n/messages'
import type { CoreFlowMap } from '../../store/slices/shared'
import type { TradingPolicy } from '../../types/contracts'

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

type BuildExecutionSummaryParams = {
  t: Translate
  broker: 'binance' | 'alpaca'
  selectedSymbol: string
  alpacaSymbol: string
  tradingPolicy?: TradingPolicy
  latestBid?: string
  latestAsk?: string
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
