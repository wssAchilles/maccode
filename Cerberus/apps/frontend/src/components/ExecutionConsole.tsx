import { useEffect } from 'react'
import { useI18n } from '../i18n/I18nProvider'
import { useCerberusStore } from '../store'

import { AlpacaPaperPanel } from './execution/AlpacaPaperPanel'
import { BinanceTestPanel } from './execution/BinanceTestPanel'
import { useAlpacaPaperTrading } from './execution/useAlpacaPaperTrading'
import { useBinanceOrderTest } from './execution/useBinanceOrderTest'

type Props = {
  selectedSymbol: string
  latestBid?: string
  latestAsk?: string
}

export function ExecutionConsole({ selectedSymbol, latestBid, latestAsk }: Props) {
  const { t } = useI18n()
  const gatewayBase = useCerberusStore((state) => state.env.gateway_base)
  const loadTradingPolicy = useCerberusStore((state) => state.executionTradingActions.loadTradingPolicy)
  const loadBinanceRule = useCerberusStore((state) => state.executionTradingActions.loadBinanceRule)
  const tradingPolicy = useCerberusStore((state) => state.executionTrading.trading_policy)
  const binanceRule = useCerberusStore((state) => state.executionTrading.binance_rule)
  const setCoreFlowStep = useCerberusStore((state) => state.uiActions.setCoreFlowStep)

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

  useEffect(() => {
    void loadTradingPolicy()
  }, [loadTradingPolicy])

  useEffect(() => {
    void loadBinanceRule(selectedSymbol)
  }, [loadBinanceRule, selectedSymbol])

  return (
    <section className="grid gap-4 lg:grid-cols-2" data-testid="execution-console">
      <BinanceTestPanel
        t={t}
        selectedSymbol={selectedSymbol}
        side={binanceModel.side}
        quantity={binanceModel.quantity}
        price={binanceModel.price}
        priceHint={binanceModel.priceHint}
        submitting={binanceModel.submitting}
        stage={binanceModel.stage}
        precheck={binanceModel.precheck}
        result={binanceModel.result}
        notional={binanceModel.notional}
        rule={binanceRule ?? null}
        policy={tradingPolicy ?? null}
        onSideChange={binanceModel.setSide}
        onQuantityChange={binanceModel.setQuantity}
        onPriceChange={binanceModel.setPrice}
        onRunPrecheck={binanceModel.runPrecheck}
        onSubmit={() => {
          void binanceModel.submit()
        }}
      />

      <AlpacaPaperPanel
        t={t}
        symbol={alpacaModel.symbol}
        quantity={alpacaModel.quantity}
        side={alpacaModel.side}
        orderType={alpacaModel.orderType}
        timeInForce={alpacaModel.timeInForce}
        limitPrice={alpacaModel.limitPrice}
        submitting={alpacaModel.submitting}
        canceling={alpacaModel.canceling}
        canCancel={alpacaModel.canCancel}
        result={alpacaModel.result}
        account={alpacaModel.account}
        policy={tradingPolicy ?? null}
        onSymbolChange={alpacaModel.setSymbol}
        onQuantityChange={alpacaModel.setQuantity}
        onSideChange={alpacaModel.setSide}
        onTypeChange={alpacaModel.setOrderType}
        onTimeInForceChange={alpacaModel.setTimeInForce}
        onLimitPriceChange={alpacaModel.setLimitPrice}
        onSubmit={() => {
          void alpacaModel.submit()
        }}
        onCancel={() => {
          void alpacaModel.cancel()
        }}
      />
    </section>
  )
}
