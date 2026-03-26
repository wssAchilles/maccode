import { useCandlesResource } from '../../app/bootstrap/useResourceQueries'
import { CandlesChart } from '../../components/CandlesChart'
import { MatchingOrderBookPanel } from '../../components/MatchingOrderBookPanel'
import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import { formatConfidence, formatPrice, summarizeLatestFeedback } from '../../view-models/workbench'
import { DiagnosticDrawer, MetricTile, SectionFrame } from '../../ui'

type Props = {
  active?: boolean
}

export function MarketWorkspace({ active = true }: Props) {
  const { t } = useI18n()
  const selectedSymbol = useCerberusStore((state) => state.marketStream.selected_symbol)
  const latest = useCerberusStore((state) => state.marketStream.latest)
  const latestBySymbol = useCerberusStore((state) => state.marketStream.latest_by_symbol)
  const latestEvent = useCerberusStore((state) => state.executionTrading.latest_event)
  const candles = useCerberusStore((state) => state.marketStream.candles)
  const summaryError = useCerberusStore((state) => state.strategySummary.last_error)
  const strategySignal = useCerberusStore((state) => state.strategySummary.signal)
  const matchingOrderBook = useCerberusStore((state) => state.strategySummary.matching_orderbook)
  const setSelectedSymbol = useCerberusStore((state) => state.marketStreamActions.setSelectedSymbol)

  useCandlesResource(active)

  const displayQuote = latestBySymbol[selectedSymbol] ?? latest

  return (
    <div className="workspace-grid">
      <SectionFrame
        title={t('workspace.market.title')}
        description={t('workspace.market.description')}
        eyebrow={t('workspace.market.eyebrow')}
        aside={
          <div className="symbol-switcher">
            {['BTCUSDT', 'ETHUSDT'].map((symbol) => (
              <button
                key={symbol}
                type="button"
                className={selectedSymbol === symbol ? 'chip-button chip-button-active' : 'chip-button'}
                onClick={() => setSelectedSymbol(symbol)}
              >
                {symbol}
              </button>
            ))}
          </div>
        }
        className="workspace-span-full"
      >
        <div className="metric-grid">
          <MetricTile label={t('market.bestBid')} value={formatPrice(displayQuote?.bid_price)} tone="positive" />
          <MetricTile label={t('market.bestAsk')} value={formatPrice(displayQuote?.ask_price)} tone="negative" />
          <MetricTile label={t('strategy.signal')} value={strategySignal?.signal ?? 'HOLD'} hint={`${t('strategy.confidence')}: ${formatConfidence(strategySignal?.confidence)}`} />
          <MetricTile label={t('market.orderStream')} value={summarizeLatestFeedback(latestEvent, undefined, t)} />
        </div>
      </SectionFrame>

      <div className="workspace-main stack">
        <SectionFrame title={`${selectedSymbol} ${t('market.candles')}`} description={t('workspace.market.chartDescription')}>
          <div className="chart-shell">
            <CandlesChart candles={candles} />
          </div>
        </SectionFrame>

        {summaryError ? (
          <DiagnosticDrawer title={t('workspace.market.diagnostics')} summary={summaryError.message}>
            <pre className="diagnostic-pre">{JSON.stringify(summaryError, null, 2)}</pre>
          </DiagnosticDrawer>
        ) : null}
      </div>

      <div className="workspace-side">
        <MatchingOrderBookPanel orderbook={matchingOrderBook} />
      </div>
    </div>
  )
}
