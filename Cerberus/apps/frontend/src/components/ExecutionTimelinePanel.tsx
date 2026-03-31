import { useDeferredValue, useId, useMemo, useState } from 'react'
import { Virtuoso } from 'react-virtuoso'

import { useRecentEventsResource } from '../app/bootstrap/useResourceQueries'
import { useI18n } from '../i18n/I18nProvider'
import { useCerberusStore } from '../store'
import { buildExecutionRows } from '../view-models/workbench'
import { EmptyState, GlassPanel } from '../ui'

function formatOptionalIso(iso: string | undefined): string {
  if (!iso) {
    return '—'
  }
  const parsed = Date.parse(iso)
  if (Number.isNaN(parsed)) {
    return iso
  }
  return new Date(parsed).toLocaleString()
}

type Props = {
  active?: boolean
}

export function ExecutionTimelinePanel({ active = true }: Props) {
  const { t } = useI18n()
  const inputId = useId()
  const orderEvents = useCerberusStore((state) => state.executionTrading.order_events)
  const filterSymbol = useCerberusStore((state) => state.executionTrading.filter_symbol)
  const filterAccountId = useCerberusStore((state) => state.executionTrading.filter_account_id)
  const filterStatus = useCerberusStore((state) => state.executionTrading.filter_status)
  const setFilters = useCerberusStore((state) => state.executionTradingActions.setFilters)
  const [search, setSearch] = useState('')
  const deferredSearch = useDeferredValue(search)

  useRecentEventsResource(active)

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

  const statusOptions = useMemo(() => {
    const values = new Set<string>()
    for (const item of orderEvents) {
      if (item.status) {
        values.add(item.status)
      }
    }
    return ['ALL', ...Array.from(values).sort()]
  }, [orderEvents])

  const filteredEvents = useMemo(() => {
    const keyword = deferredSearch.trim().toLowerCase()
    return orderEvents.filter((item) => {
      const symbolMatched = filterSymbol === 'ALL' || item.symbol === filterSymbol
      const accountMatched = filterAccountId === 'ALL' || item.account_id === filterAccountId
      const statusMatched = filterStatus === 'ALL' || item.status === filterStatus
      const searchMatched =
        keyword.length === 0 ||
        JSON.stringify(item).toLowerCase().includes(keyword)
      return symbolMatched && accountMatched && statusMatched && searchMatched
    })
  }, [deferredSearch, filterAccountId, filterStatus, filterSymbol, orderEvents])

  const rows = buildExecutionRows(filteredEvents, t)

  return (
    <article data-testid="execution-timeline-panel" className="execution-timeline">
      <div className="timeline-toolbar">
        <label className="field-label">
          {t('execution.filterSymbol')}
          <select
            id={`${inputId}-timeline-filter-symbol`}
            name="timeline_filter_symbol"
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
            id={`${inputId}-timeline-filter-account`}
            name="timeline_filter_account"
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
        <label className="field-label">
          {t('execution.filterStatus')}
          <select
            id={`${inputId}-timeline-filter-status`}
            name="timeline_filter_status"
            className="field-input"
            value={filterStatus}
            onChange={(event) => setFilters({ status: event.target.value })}
          >
            {statusOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label className="field-label">
          {t('workspace.execution.search')}
          <input
            id={`${inputId}-timeline-search`}
            name="timeline_search"
            className="field-input"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t('execution.requestId')}
          />
        </label>
      </div>

      {filteredEvents.length === 0 ? (
        <div className="execution-timeline-empty">
          <EmptyState title={t('execution.noEvents')} body={t('workspace.execution.timelineDescription')} />
        </div>
      ) : (
        <div className="execution-timeline-list">
          <Virtuoso
            style={{ height: '100%' }}
            data={filteredEvents}
            itemContent={(index, event) => {
              const row = rows[index]
              return (
                <GlassPanel className="timeline-row" tone="subtle">
                  <div className="timeline-row-main">
                    <p className="timeline-row-title">{row.title}</p>
                    <p className="timeline-row-subtitle">{row.subtitle}</p>
                    <p className="timeline-row-meta">
                      {t('execution.orderId')}: {event.order_id ?? '—'} · {t('execution.requestId')}: {event.request_id ?? '—'} · CID: {event.client_order_id ?? '—'} · {t('workspace.execution.lifecycleExecutionId')}: {event.execution_id ?? '—'}
                    </p>
                  </div>
                  <div className="timeline-row-side">
                    <p className="timeline-row-status">{row.rightTop}</p>
                    <p className="timeline-row-time">{row.rightBottom}</p>
                    <p className="timeline-row-time">
                      {t('execution.eventTime')}: {formatOptionalIso(event.event_time)}
                    </p>
                  </div>
                </GlassPanel>
              )
            }}
          />
        </div>
      )}
    </article>
  )
}
