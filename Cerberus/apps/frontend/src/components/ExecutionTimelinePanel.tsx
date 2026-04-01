import { useDeferredValue, useEffect, useId, useMemo, useRef, useState } from 'react'

import { useRecentEventsResource } from '../app/bootstrap/useResourceQueries'
import { useI18n } from '../i18n/I18nProvider'
import { useCerberusStore } from '../store'
import { useDormantSelector } from '../store/useDormantSelector'
import { EmptyState, GlassPanel } from '../ui'
import {
  buildPreparedExecutionTimeline,
  filterPreparedExecutionTimeline,
} from '../view-models/execution-timeline'

type Props = {
  active?: boolean
}

const TIMELINE_ROW_ESTIMATE_PX = 156
const TIMELINE_OVERSCAN_ROWS = 6

export function ExecutionTimelinePanel({ active = true }: Props) {
  const { t } = useI18n()
  const inputId = useId()
  const viewportRef = useRef<HTMLDivElement | null>(null)
  const orderEvents = useDormantSelector(active, (state) => state.executionTrading.order_events)
  const filterSymbol = useDormantSelector(active, (state) => state.executionTrading.filter_symbol)
  const filterAccountId = useDormantSelector(active, (state) => state.executionTrading.filter_account_id)
  const filterStatus = useDormantSelector(active, (state) => state.executionTrading.filter_status)
  const setFilters = useCerberusStore((state) => state.executionTradingActions.setFilters)
  const executionStatus = useDormantSelector(active, (state) => state.uiState.domain_status['execution-trading'])
  const [search, setSearch] = useState('')
  const [scrollTop, setScrollTop] = useState(0)
  const [viewportHeight, setViewportHeight] = useState(360)
  const deferredSearch = useDeferredValue(search)

  useRecentEventsResource(active)

  const preparedTimeline = useMemo(() => buildPreparedExecutionTimeline(orderEvents), [orderEvents])

  const filteredRowIndexes = useMemo(
    () =>
      filterPreparedExecutionTimeline({
        prepared: preparedTimeline,
        filterSymbol,
        filterAccountId,
        filterStatus,
        keyword: deferredSearch,
      }),
    [deferredSearch, filterAccountId, filterStatus, filterSymbol, preparedTimeline],
  )

  useEffect(() => {
    if (!active) {
      return
    }
    const node = viewportRef.current
    if (!node) {
      return
    }
    const updateViewport = () => {
      setViewportHeight(node.clientHeight || 360)
    }
    updateViewport()
    if (typeof ResizeObserver === 'undefined') {
      return
    }
    const observer = new ResizeObserver(updateViewport)
    observer.observe(node)
    return () => observer.disconnect()
  }, [active, filteredRowIndexes.length])

  useEffect(() => {
    setScrollTop(0)
    const viewport = viewportRef.current
    if (viewport && typeof viewport.scrollTo === 'function') {
      viewport.scrollTo({ top: 0 })
    }
  }, [filterAccountId, filterStatus, filterSymbol, deferredSearch])

  const virtualWindow = useMemo(() => {
    const visibleCount = Math.ceil(viewportHeight / TIMELINE_ROW_ESTIMATE_PX) + TIMELINE_OVERSCAN_ROWS * 2
    const startIndex = Math.max(0, Math.floor(scrollTop / TIMELINE_ROW_ESTIMATE_PX) - TIMELINE_OVERSCAN_ROWS)
    const endIndex = Math.min(filteredRowIndexes.length, startIndex + visibleCount)
    return {
      startIndex,
      endIndex,
      topSpacerHeight: startIndex * TIMELINE_ROW_ESTIMATE_PX,
      bottomSpacerHeight: Math.max(0, (filteredRowIndexes.length - endIndex) * TIMELINE_ROW_ESTIMATE_PX),
      visibleRows: filteredRowIndexes
        .slice(startIndex, endIndex)
        .map((rowIndex) => preparedTimeline.rows[rowIndex]),
    }
  }, [filteredRowIndexes, preparedTimeline.rows, scrollTop, viewportHeight])

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

      {filteredRowIndexes.length === 0 ? (
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
        <div
          ref={viewportRef}
          className="execution-timeline-list"
          onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
        >
          {virtualWindow.topSpacerHeight > 0 ? (
            <div style={{ height: `${virtualWindow.topSpacerHeight}px` }} aria-hidden="true" />
          ) : null}
          {virtualWindow.visibleRows.map((row) => (
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
                <p className="tr-time">{t('execution.receivedAt')}: {row.receivedAtLabel}</p>
                <p className="tr-time">
                  {t('execution.eventTime')}: {row.eventTimeLabel}
                </p>
              </div>
            </GlassPanel>
          ))}
          {virtualWindow.bottomSpacerHeight > 0 ? (
            <div style={{ height: `${virtualWindow.bottomSpacerHeight}px` }} aria-hidden="true" />
          ) : null}
        </div>
      )}
    </article>
  )
}
