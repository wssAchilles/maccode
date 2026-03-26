import { startTransition, useMemo, useState } from 'react'
import type { TranslationKey } from '../i18n/messages'
import { useI18n } from '../i18n/I18nProvider'
import { useCerberusStore } from '../store'

import { AlpacaPaperPanel } from './execution/AlpacaPaperPanel'
import { BinanceTestPanel } from './execution/BinanceTestPanel'
import { useAlpacaPaperTrading } from './execution/useAlpacaPaperTrading'
import { useBinanceOrderTest } from './execution/useBinanceOrderTest'
import { useBinanceRuleResource, useTradingPolicyResource } from '../app/bootstrap/useResourceQueries'
import { DataList, GlassPanel, StatusPill } from '../ui'

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
  const coreFlow = useCerberusStore((state) => state.uiState.core_flow)
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

  const progressItems = useMemo(
    () =>
      EXECUTION_PROGRESS_STEPS.map((step) => {
        const item = coreFlow[step]
        return {
          id: step,
          title: t(EXECUTION_STEP_LABELS[step]),
          state: item.state,
          stateLabel: t(FLOW_STATE_LABELS[item.state]),
          reason: item.reason?.trim() ? item.reason : t('common.na'),
          requestId: item.request_id,
        }
      }),
    [coreFlow, t],
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
          <div className="execution-side-copy">
            <p className="subtle-label">{t('workspace.execution.diagnostics')}</p>
            <p className="panel-caption">{t('workspace.execution.ticketDescription')}</p>
          </div>
          <DataList items={executionSummary} />
          <div className="execution-progress">
            {progressItems.map((item, index) => (
              <div key={item.id} className="execution-progress-item">
                <div className="execution-progress-rail" aria-hidden="true">
                  <span
                    className={
                      item.state === 'success'
                        ? 'execution-progress-dot execution-progress-dot-success'
                        : item.state === 'error'
                          ? 'execution-progress-dot execution-progress-dot-error'
                          : item.state === 'active'
                            ? 'execution-progress-dot execution-progress-dot-active'
                            : 'execution-progress-dot'
                    }
                  />
                  {index < progressItems.length - 1 ? <span className="execution-progress-line" /> : null}
                </div>
                <div className="execution-progress-copy">
                  <div className="execution-progress-head">
                    <p className="execution-progress-title">{item.title}</p>
                    <StatusPill state={item.state} label={item.stateLabel} compact />
                  </div>
                  <p className="execution-progress-reason">{item.reason}</p>
                  {item.requestId ? <p className="execution-progress-request">rid: {item.requestId}</p> : null}
                </div>
              </div>
            ))}
          </div>
        </GlassPanel>
      </div>
    </section>
  )
}
