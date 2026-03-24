import { useMemo, useState } from 'react'

import { useI18n } from '../i18n/I18nProvider'
import { useCerberusStore } from '../store'

const ROW_HEIGHT = 76
const VIEWPORT_HEIGHT = 320

function formatTimestamp(timestamp: number): string {
  return new Date(timestamp).toLocaleString()
}

export function ExecutionTimelinePanel() {
  const { t } = useI18n()
  const orderEvents = useCerberusStore((state) => state.executionTrading.order_events)
  const filterSymbol = useCerberusStore((state) => state.executionTrading.filter_symbol)
  const filterAccountId = useCerberusStore((state) => state.executionTrading.filter_account_id)
  const setFilters = useCerberusStore((state) => state.executionTradingActions.setFilters)
  const [scrollTop, setScrollTop] = useState(0)

  const symbolOptions = useMemo(() => {
    const values = new Set<string>()
    for (const item of orderEvents) {
      if (item.symbol) {
        values.add(item.symbol)
      }
    }
    return ['ALL', ...Array.from(values).sort()]
  }, [orderEvents])

  const accountOptions = useMemo(() => {
    const values = new Set<string>()
    for (const item of orderEvents) {
      if (item.account_id) {
        values.add(item.account_id)
      }
    }
    return ['ALL', ...Array.from(values).sort()]
  }, [orderEvents])

  const filteredEvents = useMemo(() => {
    return orderEvents.filter((item) => {
      const symbolMatched = filterSymbol === 'ALL' || item.symbol === filterSymbol
      const accountMatched = filterAccountId === 'ALL' || item.account_id === filterAccountId
      return symbolMatched && accountMatched
    })
  }, [filterAccountId, filterSymbol, orderEvents])

  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - 4)
  const visibleCount = Math.ceil(VIEWPORT_HEIGHT / ROW_HEIGHT) + 8
  const endIndex = Math.min(filteredEvents.length, startIndex + visibleCount)
  const visibleRows = filteredEvents.slice(startIndex, endIndex)
  const paddingTop = startIndex * ROW_HEIGHT
  const paddingBottom = Math.max(0, (filteredEvents.length - endIndex) * ROW_HEIGHT)

  return (
    <article className="panel-card" data-testid="execution-timeline-panel">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="panel-title">{t('execution.timeline')}</h2>
        <div className="grid gap-2 text-xs sm:grid-cols-2">
          <label className="field-label">
            {t('execution.filterSymbol')}
            <select
              className="field-input"
              value={filterSymbol}
              onChange={(event) => setFilters({ symbol: event.target.value })}
            >
              {symbolOptions.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="field-label">
            {t('execution.filterAccount')}
            <select
              className="field-input"
              value={filterAccountId}
              onChange={(event) => setFilters({ account_id: event.target.value })}
            >
              {accountOptions.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {filteredEvents.length === 0 ? (
        <p className="text-xs text-slate-400">{t('execution.noEvents')}</p>
      ) : (
        <div
          className="overflow-y-auto rounded-xl border border-slate-700/60 bg-slate-950/45"
          style={{ height: VIEWPORT_HEIGHT }}
          onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
        >
          <div style={{ paddingTop, paddingBottom }}>
            {visibleRows.map((event) => (
              <div
                key={event.id}
                className="grid grid-cols-[1.3fr_1fr_1fr] gap-2 border-b border-slate-800/80 px-3 py-2 text-xs"
              >
                <div>
                  <p className="font-semibold text-cyan-200">{event.event_type}</p>
                  <p className="text-[11px] text-slate-500">{event.channel}</p>
                </div>
                <div>
                  <p className="text-slate-300">{event.symbol ?? '-'}</p>
                  <p className="text-[11px] text-slate-500">{event.account_id ?? '-'}</p>
                </div>
                <div className="text-right">
                  <p className="text-slate-300">{event.status ?? '-'}</p>
                  <p className="text-[11px] text-slate-500">{formatTimestamp(event.received_at)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </article>
  )
}
