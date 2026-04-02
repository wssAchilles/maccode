import { useI18n } from '../i18n/I18nProvider'

import { AlpacaPaperPanel } from './execution/AlpacaPaperPanel'
import { BinanceTestPanel } from './execution/BinanceTestPanel'
import { GlassPanel, MotionSurface, StatusPill, WorkspaceOperatorDeck, WorkspaceSpotlight } from '../ui'
import { useExecutionConsoleModel } from '../features/execution/useExecutionConsoleModel'
import { useRafPresenceTransition } from '../ui/motion/useRafPresenceTransition'

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
    deskSpotlight,
    deskSections,
    progressItems,
  } = useExecutionConsoleModel({
    active,
    selectedSymbol,
    latestBid,
    latestAsk,
  })
  const brokerPhase = useRafPresenceTransition(broker, 320)

  return (
    <section className="execution-orchestrator" data-testid="execution-console">
      <WorkspaceSpotlight model={deskSpotlight} compact className="execution-desk-spotlight" />

      <div
        className="broker-tabs"
        role="tablist"
        aria-label={t('workspace.execution.ticketTitle')}
        data-broker={broker}
        data-phase={brokerPhase}
      >
        <span className="broker-tabs-indicator" aria-hidden="true" />
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
        <div className="xlay-main">
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

        <MotionSurface className="xlay-side-shell" mode="panel">
          <GlassPanel className="xlay-side" tone="subtle">
            <div className="xs-copy">
              <p className="subtle-label">{t('workspace.execution.diagnostics')}</p>
              <p className="panel-caption">{t('workspace.execution.ticketDescription')}</p>
            </div>
            <WorkspaceOperatorDeck sections={deskSections} layout="stack" />
            <div className="xp">
              {progressItems.map((item, index) => (
                <div key={item.id} className="xp-item">
                  <div className="xp-rail" aria-hidden="true">
                    <span
                      className={
                        item.state === 'success'
                          ? 'xp-dot xp-dot-success'
                          : item.state === 'error'
                            ? 'xp-dot xp-dot-error'
                            : item.state === 'active'
                              ? 'xp-dot xp-dot-active'
                              : 'xp-dot'
                      }
                    />
                    {index < progressItems.length - 1 ? <span className="xp-line" /> : null}
                  </div>
                  <div className="xp-copy">
                    <div className="xp-head">
                      <p className="xp-title">{item.title}</p>
                      <StatusPill state={item.state} label={item.stateLabel} compact />
                    </div>
                    <p className="xp-reason">{item.reason}</p>
                    {item.requestId ? <p className="xp-request">rid: {item.requestId}</p> : null}
                  </div>
                </div>
              ))}
            </div>
          </GlassPanel>
        </MotionSurface>
      </div>
    </section>
  )
}
