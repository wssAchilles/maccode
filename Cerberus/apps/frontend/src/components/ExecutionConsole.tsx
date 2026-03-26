import { startTransition, useMemo, useState } from 'react'
import { useI18n } from '../i18n/I18nProvider'
import { useCerberusStore } from '../store'

import { AlpacaPaperPanel } from './execution/AlpacaPaperPanel'
import { BinanceTestPanel } from './execution/BinanceTestPanel'
import { useAlpacaPaperTrading } from './execution/useAlpacaPaperTrading'
import { useBinanceOrderTest } from './execution/useBinanceOrderTest'
import { useBinanceRuleResource, useTradingPolicyResource } from '../app/bootstrap/useResourceQueries'
import { DataList, GlassPanel } from '../ui'

type Props = {
  active?: boolean
  selectedSymbol: string
  latestBid?: string
  latestAsk?: string
}

export function ExecutionConsole({ active = true, selectedSymbol, latestBid, latestAsk }: Props) {
  const { t } = useI18n()
  const [broker, setBroker] = useState<'binance' | 'alpaca'>('binance')
  const gatewayBase = useCerberusStore((state) => state.env.gateway_base)
  const tradingPolicy = useCerberusStore((state) => state.executionTrading.trading_policy)
  const binanceRule = useCerberusStore((state) => state.executionTrading.binance_rule)
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
    () => [
      {
        id: 'symbol',
        label: 'Symbol',
        value: broker === 'binance' ? selectedSymbol : alpacaModel.symbol.toUpperCase(),
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
    ],
    [alpacaModel.symbol, broker, latestAsk, latestBid, selectedSymbol, t, tradingPolicy?.enforced],
  )

  return (
    <section className="execution-orchestrator" data-testid="execution-console">
      <div className="broker-tabs" role="tablist" aria-label={t('workspace.execution.ticketTitle')}>
        <button
          type="button"
          role="tab"
          aria-selected={broker === 'binance'}
          className={broker === 'binance' ? 'chip-button chip-button-active' : 'chip-button'}
          onClick={() => startTransition(() => setBroker('binance'))}
        >
          Binance
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={broker === 'alpaca'}
          className={broker === 'alpaca' ? 'chip-button chip-button-active' : 'chip-button'}
          onClick={() => startTransition(() => setBroker('alpaca'))}
        >
          Alpaca
        </button>
      </div>

      <div className="execution-layout">
        <div className="execution-layout-main">
          {broker === 'binance' ? (
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
          ) : (
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
          )}
        </div>

        <GlassPanel className="execution-layout-side" tone="subtle">
          <p className="subtle-label">{t('workspace.execution.ticketDescription')}</p>
          <DataList items={executionSummary} />
        </GlassPanel>
      </div>
    </section>
  )
}
