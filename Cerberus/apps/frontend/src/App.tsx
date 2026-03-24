import { useEffect } from 'react'

import {
  AppHeader,
  ExecutionSection,
  HealthSection,
  MarketSection,
  TradingSection,
} from './app/sections'
import { useI18n } from './i18n/I18nProvider'
import { useCerberusStore } from './store'

function toOrderSummary(event: {
  event_type: string
  symbol?: string
  status?: string
} | null): string {
  if (!event) {
    return ''
  }
  return `${event.event_type} ${event.symbol ?? ''} ${event.status ?? ''}`.trim()
}

export default function App() {
  const { locale, setLocale: setI18nLocale, t } = useI18n()

  const env = useCerberusStore((state) => state.env)
  const selectedSymbol = useCerberusStore((state) => state.marketStream.selected_symbol)
  const latest = useCerberusStore((state) => state.marketStream.latest)
  const latestBySymbol = useCerberusStore((state) => state.marketStream.latest_by_symbol)
  const candles = useCerberusStore((state) => state.marketStream.candles)
  const strategySignal = useCerberusStore((state) => state.strategySummary.signal)
  const recentSignals = useCerberusStore((state) => state.strategySummary.recent_signals)
  const persistenceStatus = useCerberusStore((state) => state.strategySummary.persistence_status)
  const matchingOrderBook = useCerberusStore((state) => state.strategySummary.matching_orderbook)
  const summaryError = useCerberusStore((state) => state.strategySummary.last_error)
  const latestEvent = useCerberusStore((state) => state.executionTrading.latest_event)
  const heartbeat = useCerberusStore((state) => state.executionTrading.heartbeat)

  const storeLocale = useCerberusStore((state) => state.uiState.locale)
  const domainStatus = useCerberusStore((state) => state.uiState.domain_status)
  const liveAnnouncement = useCerberusStore((state) => state.uiState.live_announcement)

  const announce = useCerberusStore((state) => state.uiActions.announce)
  const setStoreLocale = useCerberusStore((state) => state.uiActions.setLocale)
  const recomputeStaleFlags = useCerberusStore((state) => state.uiActions.recomputeStaleFlags)

  const setSelectedSymbol = useCerberusStore((state) => state.marketStreamActions.setSelectedSymbol)
  const connectMarketSocket = useCerberusStore((state) => state.marketStreamActions.connectMarketSocket)
  const loadCandles = useCerberusStore((state) => state.marketStreamActions.loadCandles)
  const connectOrdersSocket = useCerberusStore((state) => state.executionTradingActions.connectOrdersSocket)
  const loadRecentOrderEvents = useCerberusStore(
    (state) => state.executionTradingActions.loadRecentOrderEvents,
  )
  const loadTradingPolicy = useCerberusStore((state) => state.executionTradingActions.loadTradingPolicy)
  const loadBinanceRule = useCerberusStore((state) => state.executionTradingActions.loadBinanceRule)
  const refreshSummary = useCerberusStore((state) => state.strategySummaryActions.refreshSummary)

  const displayQuote = latestBySymbol[selectedSymbol] ?? latest
  const orderSummary = latestEvent ? toOrderSummary(latestEvent) : heartbeat ?? t('common.heartbeat')

  useEffect(() => {
    if (storeLocale !== locale) {
      setI18nLocale(storeLocale)
    }
  }, [locale, setI18nLocale, storeLocale])

  useEffect(() => {
    void import('./lib/firebase').then((module) => {
      module.initFirebase()
    })
    connectMarketSocket()
    connectOrdersSocket()
    void loadRecentOrderEvents()
    void loadTradingPolicy()
    void loadCandles()
    void loadBinanceRule(selectedSymbol)
    void refreshSummary()

    const summaryTimer = window.setInterval(() => {
      void refreshSummary()
    }, 4_000)

    const staleTimer = window.setInterval(() => {
      recomputeStaleFlags()
    }, 2_000)

    return () => {
      window.clearInterval(summaryTimer)
      window.clearInterval(staleTimer)
    }
  }, [
    connectMarketSocket,
    connectOrdersSocket,
    loadRecentOrderEvents,
    loadBinanceRule,
    loadCandles,
    loadTradingPolicy,
    recomputeStaleFlags,
    refreshSummary,
    selectedSymbol,
  ])

  useEffect(() => {
    void loadCandles()
    void loadBinanceRule(selectedSymbol)
    void refreshSummary()
  }, [loadBinanceRule, loadCandles, refreshSummary, selectedSymbol])

  useEffect(() => {
    if (summaryError) {
      announce(summaryError)
    }
  }, [announce, summaryError])

  return (
    <main className="mx-auto max-w-7xl p-4 text-white md:p-6" data-testid="app-shell">
      <AppHeader
        t={t}
        env={env}
        locale={storeLocale}
        liveAnnouncement={liveAnnouncement}
        onLocaleChange={setStoreLocale}
      />

      <MarketSection
        t={t}
        selectedSymbol={selectedSymbol}
        displayQuote={displayQuote}
        latestEvent={latestEvent}
        orderSummary={orderSummary}
        candles={candles}
        onSymbolSelect={setSelectedSymbol}
      />

      <TradingSection
        t={t}
        selectedSymbol={selectedSymbol}
        latestBid={displayQuote?.bid_price}
        latestAsk={displayQuote?.ask_price}
      />

      <ExecutionSection
        t={t}
        selectedSymbol={selectedSymbol}
        strategySignal={strategySignal}
        recentSignals={recentSignals}
        persistenceStatus={persistenceStatus}
        summaryError={summaryError}
        matchingOrderBook={matchingOrderBook}
      />

      <HealthSection domainStatus={domainStatus} persistenceStatus={persistenceStatus} />
    </main>
  )
}
