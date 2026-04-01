import { useDeferredValue, useId, useMemo, useState } from 'react'

import { useRecentEventsResource } from '../app/bootstrap/useResourceQueries'
import { useI18n } from '../i18n/I18nProvider'
import { useCerberusStore } from '../store'
import { useDormantSelector } from '../store/useDormantSelector'
import { EmptyState, GlassPanel } from '../ui'
import type { OrderTimelineEvent } from '../types/contracts'

function formatOptionalIso(value: string | number | undefined): string {
  if (value === undefined || value === null) {
    return '—'
  }
  const parsed = typeof value === 'number' ? value : Date.parse(value)
  if (Number.isNaN(parsed)) {
    return String(value)
  }
  return new Date(parsed).toLocaleString()
}

type Props = {
  active?: boolean
}

type PreparedTimelineRow = {
  id: string
  event: OrderTimelineEvent
  title: string
  subtitle: string
  rightTop: string
  rightBottom: string
  eventTimeLabel: string
  searchText: string
}

export function ExecutionTimelinePanel({ active = true }: Props) {
  const { t } = useI18n()
  const inputId = useId()
  const orderEvents = useDormantSelector(active, (state) => state.executionTrading.order_events)
  const filterSymbol = useDormantSelector(active, (state) => state.executionTrading.filter_symbol)
  const filterAccountId = useDormantSelector(active, (state) => state.executionTrading.filter_account_id)
  const filterStatus = useDormantSelector(active, (state) => state.executionTrading.filter_status)
  const setFilters = useCerberusStore((state) => state.executionTradingActions.setFilters)
  const executionStatus = useDormantSelector(active, (state) => state.uiState.domain_status['execution-trading'])
  const [search, setSearch] = useState('')
  const deferredSearch = useDeferredValue(search)

  useRecentEventsResource(active)

  const preparedTimeline = useMemo(() => {
    const symbols = new Set<string>()
    const accounts = new Set<string>()
    const statuses = new Set<string>()
    const rows: PreparedTimelineRow[] = []

    for (const event of orderEvents) {
      if (event.symbol) {
        symbols.add(event.symbol)
      }
      if (event.account_id) {
        accounts.add(event.account_id)
      }
      if (event.status) {
        statuses.add(event.status)
      }

      const title = `${event.event_type} · ${event.lifecycle_phase}`
      const subtitle = [
        event.symbol ?? '—',
        event.account_id ?? '—',
        event.client_order_id ?? event.request_id ?? '—',
      ].join(' · ')
      const rightTop = event.status ?? event.lifecycle_phase
      const rightBottom = `${t('execution.receivedAt')}: ${formatOptionalIso(event.received_at)}`
      const eventTimeLabel = formatOptionalIso(event.event_time)
      const searchText = [
        event.symbol,
        event.account_id,
        event.status,
        event.order_id,
        event.request_id,
        event.client_order_id,
        event.execution_id,
        event.lifecycle_phase,
        event.event_type,
        event.reason,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      rows.push({
        id: event.id,
        event,
        title,
        subtitle,
        rightTop,
        rightBottom,
        eventTimeLabel,
        searchText,
      })
    }

    return {
      rows,
      symbolOptions: ['ALL', ...Array.from(symbols).sort()],
      accountOptions: ['ALL', ...Array.from(accounts).sort()],
      statusOptions: ['ALL', ...Array.from(statuses).sort()],
    }
  }, [orderEvents, t])

  const filteredRows = useMemo(() => {
    const keyword = deferredSearch.trim().toLowerCase()
    return preparedTimeline.rows.filter((row) => {
      const { event } = row
      const symbolMatched = filterSymbol === 'ALL' || event.symbol === filterSymbol
      const accountMatched = filterAccountId === 'ALL' || event.account_id === filterAccountId
      const statusMatched = filterStatus === 'ALL' || event.status === filterStatus
      const searchMatched = keyword.length === 0 || row.searchText.includes(keyword)
      return symbolMatched && accountMatched && statusMatched && searchMatched
    })
  }, [deferredSearch, filterAccountId, filterStatus, filterSymbol, preparedTimeline.rows])

  return (
    <article data-testid="execution-timeline-panel" className="execution-timeline">
      {filterSymbol !== 'ALL' ? (
        <div className="xtl">
          <p className="subtle-label">{t('workspace.execution.linkageTitle')}</p>
          <p className="sp-hint">{t('workspace.execution.linkageHint').replace('{symbol}', filterSymbol)}</p>
        </div>
      ) : null}
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
            {preparedTimeline.symbolOptions.map((value) => (
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
            {preparedTimeline.accountOptions.map((value) => (
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
            {preparedTimeline.statusOptions.map((value) => (
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

      {filteredRows.length === 0 ? (
        <div className="execution-timeline-empty">
          <EmptyState
            title={
              executionStatus.state === 'error'
                ? t('execution.timelineErrorTitle')
                : orderEvents.length > 0
                  ? t('execution.timelineFilteredEmptyTitle')
                  : t('execution.noEvents')
            }
            body={
              executionStatus.state === 'error'
                ? executionStatus.reason ?? t('execution.timelineRetryHint')
                : executionStatus.stale
                  ? t('execution.timelineStaleHint')
                  : orderEvents.length > 0
                    ? t('execution.timelineFilteredEmptyHint')
                    : t('workspace.execution.timelineDescription')
            }
          />
        </div>
      ) : (
        <div className="execution-timeline-list">
          {filteredRows.map((row) => (
            <GlassPanel key={row.id} className="timeline-row" tone="subtle">
              <div className="tr-main">
                <p className="tr-title">{row.title}</p>
                <p className="tr-subtitle">{row.subtitle}</p>
                <p className="tr-meta">
                  {t('execution.orderId')}: {row.event.order_id ?? '—'} · {t('execution.requestId')}: {row.event.request_id ?? '—'} · CID: {row.event.client_order_id ?? '—'} · {t('workspace.execution.lifecycleExecutionId')}: {row.event.execution_id ?? '—'}
                </p>
              </div>
              <div className="tr-side">
                <p className="tr-status">{row.rightTop}</p>
                <p className="tr-time">{row.rightBottom}</p>
                <p className="tr-time">
                  {t('execution.eventTime')}: {row.eventTimeLabel}
                </p>
              </div>
            </GlassPanel>
          ))}
        </div>
      )}
    </article>
  )
}
