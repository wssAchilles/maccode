import { startTransition, useMemo, useState } from 'react'
import { useShallow } from 'zustand/react/shallow'

import { useTradingPolicyResource, useBinanceRuleResource } from '../../app/bootstrap/useResourceQueries'
import { useCerberusStore } from '../../store'
import { useDormantSelector } from '../../store/useDormantSelector'
import { useI18n } from '../../i18n/I18nProvider'
import { useAlpacaPaperTrading } from '../../components/execution/useAlpacaPaperTrading'
import { useBinanceOrderTest } from '../../components/execution/useBinanceOrderTest'

import { buildExecutionDeskSpotlightModel, buildExecutionProgressItems, buildExecutionSummary } from './view-models'

type Params = {
  active: boolean
  selectedSymbol: string
  latestBid?: string
  latestAsk?: string
}

export function useExecutionConsoleModel({
  active,
  selectedSymbol,
  latestBid,
  latestAsk,
}: Params) {
  const { t } = useI18n()
  const [broker, setBrokerState] = useState<'binance' | 'alpaca'>('binance')
  const { gatewayBase, tradingPolicy, binanceRule, coreFlow } = useDormantSelector(
    active,
    useShallow((state) => ({
      gatewayBase: state.env.gateway_base,
      tradingPolicy: state.executionTrading.trading_policy,
      binanceRule: state.executionTrading.binance_rule,
      coreFlow: state.uiState.core_flow,
    })),
  )
  const setCoreFlowStep = useCerberusStore((state) => state.uiActions.setCoreFlowStep)

  useTradingPolicyResource(active)
  useBinanceRuleResource(active && broker === 'binance', selectedSymbol)

  const binanceModel = useBinanceOrderTest({
    selectedSymbol,
    latestBid,
    latestAsk,
    gatewayBase,
    rule: binanceRule ?? null,
    policy: tradingPolicy ?? null,
    onFlowEvent: (event) => {
      setCoreFlowStep(event.step, {
        state: event.state,
        reason: event.reason,
        request_id: event.requestId,
      })
    },
  })

  const alpacaModel = useAlpacaPaperTrading({
    active: active && broker === 'alpaca',
    gatewayBase,
    tradingPolicy: tradingPolicy ?? null,
    onFlowEvent: (event) => {
      setCoreFlowStep(event.step, {
        state: event.state,
        reason: event.reason,
        request_id: event.requestId,
      })
    },
  })

  const executionSummary = useMemo(
    () =>
      buildExecutionSummary({
        t,
        broker,
        selectedSymbol,
        alpacaSymbol: alpacaModel.symbol,
        tradingPolicy,
        latestBid,
        latestAsk,
      }),
    [alpacaModel.symbol, broker, latestAsk, latestBid, selectedSymbol, t, tradingPolicy],
  )

  const progressItems = useMemo(
    () => buildExecutionProgressItems(coreFlow, t),
    [coreFlow, t],
  )

  const deskSpotlight = useMemo(
    () =>
      buildExecutionDeskSpotlightModel({
        t,
        broker,
        selectedSymbol,
        alpacaSymbol: alpacaModel.symbol,
        tradingPolicy,
        latestBid,
        latestAsk,
        binanceRule,
      }),
    [alpacaModel.symbol, binanceRule, broker, latestAsk, latestBid, selectedSymbol, t, tradingPolicy],
  )

  return {
    broker,
    setBroker: (nextBroker: 'binance' | 'alpaca') => {
      startTransition(() => setBrokerState(nextBroker))
    },
    tradingPolicy,
    binanceRule,
    binanceModel,
    alpacaModel,
    deskSpotlight,
    executionSummary,
    progressItems,
  }
}
