import { startTransition, useMemo, useState } from 'react'
import { useShallow } from 'zustand/react/shallow'

import { useTradingPolicyResource, useBinanceRuleResource } from '../../app/bootstrap/useResourceQueries'
import { useCerberusStore } from '../../store'
import { useDormantSelector } from '../../store/useDormantSelector'
import { useI18n } from '../../i18n/I18nProvider'
import { useAlpacaPaperTrading } from '../../components/execution/useAlpacaPaperTrading'
import { useBinanceOrderTest } from '../../components/execution/useBinanceOrderTest'

import {
  buildExecutionDeskContextModel,
  buildExecutionDeskSections,
  buildExecutionDeskSpotlightModel,
  buildExecutionProgressItems,
} from './view-models'

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

  const consoleModel = useMemo(() => ({
    deskContext: buildExecutionDeskContextModel({
      t,
      broker,
      selectedSymbol,
      alpacaSymbol: alpacaModel.symbol,
      tradingPolicy,
      latestBid,
      latestAsk,
      binanceRule,
    }),
    deskSections: buildExecutionDeskSections({
      t,
      broker,
      selectedSymbol,
      alpacaSymbol: alpacaModel.symbol,
      tradingPolicy,
      latestBid,
      latestAsk,
      binanceRule,
      alpacaAccountLabel:
        alpacaModel.account?.body && typeof alpacaModel.account.body === 'object'
          ? ((alpacaModel.account.body as { account_number?: unknown }).account_number as string | undefined)
          : undefined,
    }),
    progressItems: buildExecutionProgressItems(coreFlow, t),
    deskSpotlight: buildExecutionDeskSpotlightModel({
      t,
      broker,
      selectedSymbol,
      alpacaSymbol: alpacaModel.symbol,
      tradingPolicy,
      latestBid,
      latestAsk,
      binanceRule,
    }),
  }), [alpacaModel.account?.body, alpacaModel.symbol, binanceRule, broker, coreFlow, latestAsk, latestBid, selectedSymbol, t, tradingPolicy])

  return {
    broker,
    setBroker: (nextBroker: 'binance' | 'alpaca') => {
      startTransition(() => setBrokerState(nextBroker))
    },
    tradingPolicy,
    binanceRule,
    binanceModel,
    alpacaModel,
    ...consoleModel,
  }
}
