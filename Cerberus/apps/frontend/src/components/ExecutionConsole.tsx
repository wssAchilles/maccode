import { useI18n } from '../i18n/I18nProvider'

import { AlpacaPaperPanel } from './execution/AlpacaPaperPanel'
import { BinanceTestPanel } from './execution/BinanceTestPanel'
import { DataList, GlassPanel, StatusPill } from '../ui'
import { useExecutionConsoleModel } from '../features/execution/useExecutionConsoleModel'

type Props = {
  active?: boolean
  selectedSymbol: string
  latestBid?: string
  latestAsk?: string
}

export function ExecutionConsole({ active = true, selectedSymbol, latestBid, latestAsk }: Props) {
  const { t } = useI18n()
  const {
    broker,
    setBroker,
    tradingPolicy,
    binanceRule,
    binanceModel,
    alpacaModel,
    executionSummary,
    progressItems,
  } = useExecutionConsoleModel({
    active,
    selectedSymbol,
    latestBid,
    latestAsk,
  })

  return (
    <section className="execution-orchestrator" data-testid="execution-console">
      <div className="broker-tabs" role="tablist" aria-label={t('workspace.execution.ticketTitle')}>
        <button
          type="button"
          role="tab"
          aria-selected={broker === 'binance'}
          className={broker === 'binance' ? 'chip-button chip-button-active' : 'chip-button'}
          onClick={() => setBroker('binance')}
        >
          Binance
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={broker === 'alpaca'}
          className={broker === 'alpaca' ? 'chip-button chip-button-active' : 'chip-button'}
          onClick={() => setBroker('alpaca')}
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
