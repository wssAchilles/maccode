import { useDeferredValue, useEffect, useId, useMemo, useRef, useState } from 'react'
import { useShallow } from 'zustand/react/shallow'

import { useRecentEventsResource } from '../app/bootstrap/useResourceQueries'
import { useI18n } from '../i18n/I18nProvider'
import { useCerberusStore } from '../store'
import { useDormantSelector } from '../store/useDormantSelector'
import { EmptyState, GlassPanel } from '../ui'
import {
  buildPreparedExecutionTimeline,
  buildPreparedExecutionTimelineWindow,
  filterPreparedExecutionTimeline,
  getExecutionTimelineWindowAnchor,
} from '../view-models/execution-timeline'

type Props = {
  active?: boolean
}

const TIMELINE_ROW_ESTIMATE_PX = 168
const TIMELINE_OVERSCAN_ROWS = 6

export function ExecutionTimelinePanel({ active = true }: Props) {
  const { t } = useI18n()
  const inputId = useId()
  const viewportRef = useRef<HTMLDivElement | null>(null)
  const scrollFrameRef = useRef<number | null>(null)
  const windowAnchorRef = useRef(0)
  const { orderEvents, filterSymbol, filterAccountId, filterStatus, executionStatus } = useDormantSelector(
    active,
    useShallow((state) => ({
      orderEvents: state.executionTrading.order_events,
      filterSymbol: state.executionTrading.filter_symbol,
      filterAccountId: state.executionTrading.filter_account_id,
      filterStatus: state.executionTrading.filter_status,
      executionStatus: state.uiState.domain_status['execution-trading'],
    })),
  )
  const setFilters = useCerberusStore((state) => state.executionTradingActions.setFilters)
  const [search, setSearch] = useState('')
  const [windowAnchor, setWindowAnchor] = useState(0)
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
    return () => {
      if (scrollFrameRef.current !== null) {
        cancelAnimationFrame(scrollFrameRef.current)
      }
    }
  }, [])

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
    windowAnchorRef.current = 0
    setWindowAnchor(0)
    const viewport = viewportRef.current
    if (viewport && typeof viewport.scrollTo === 'function') {
      viewport.scrollTo({ top: 0 })
    }
  }, [filterAccountId, filterStatus, filterSymbol, deferredSearch])

  const virtualWindow = useMemo(() => {
    const window = buildPreparedExecutionTimelineWindow({
      rowIndexes: filteredRowIndexes,
      viewportHeight,
      rowHeight: TIMELINE_ROW_ESTIMATE_PX,
      overscanRows: TIMELINE_OVERSCAN_ROWS,
      anchorIndex: windowAnchor,
    })

    return {
      ...window,
      visibleRows: window.visibleRowIndexes.map((rowIndex) => preparedTimeline.rows[rowIndex]),
    }
  }, [filteredRowIndexes, preparedTimeline.rows, viewportHeight, windowAnchor])

  const handleScroll = (scrollTop: number) => {
    const nextAnchor = getExecutionTimelineWindowAnchor(
      scrollTop,
      TIMELINE_ROW_ESTIMATE_PX,
      TIMELINE_OVERSCAN_ROWS,
    )
    if (nextAnchor === windowAnchorRef.current) {
      return
    }
    windowAnchorRef.current = nextAnchor
    setWindowAnchor(nextAnchor)
  }

  const scheduleScrollWindowUpdate = (scrollTop: number) => {
    if (scrollFrameRef.current !== null) {
      cancelAnimationFrame(scrollFrameRef.current)
    }
    scrollFrameRef.current = requestAnimationFrame(() => {
      scrollFrameRef.current = null
      handleScroll(scrollTop)
    })
  }

  return (
    <article data-testid="execution-timeline-panel" className="xtm">
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
        <div className="xtm-empty">
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
          className="xtm-list"
          onScroll={(event) => scheduleScrollWindowUpdate(event.currentTarget.scrollTop)}
        >
          {virtualWindow.topSpacerHeight > 0 ? (
            <div style={{ height: `${virtualWindow.topSpacerHeight}px` }} aria-hidden="true" />
          ) : null}
          {virtualWindow.visibleRows.map((row) => (
            <GlassPanel key={row.id} className="timeline-row" tone="subtle">
              <div className="tr-main">
                <p className="tr-title">{row.title}</p>
                <p className="tr-subtitle">{row.subtitle}</p>
                <div className="tr-meta-grid">
                  <div className="tr-meta-line">
                    <span className="tr-meta-key">{t('execution.orderId')}</span>
                    <span className="tr-meta-value" title={row.orderIdLabel}>
                      {row.orderIdLabel}
                    </span>
                  </div>
                  <div className="tr-meta-line">
                    <span className="tr-meta-key">{t('execution.requestId')}</span>
                    <span className="tr-meta-value" title={row.requestIdLabel}>
                      {row.requestIdLabel}
                    </span>
                  </div>
                  <div className="tr-meta-line">
                    <span className="tr-meta-key">CID</span>
                    <span className="tr-meta-value" title={row.clientOrderIdLabel}>
                      {row.clientOrderIdLabel}
                    </span>
                  </div>
                  <div className="tr-meta-line">
                    <span className="tr-meta-key">{t('workspace.execution.lifecycleExecutionId')}</span>
                    <span className="tr-meta-value" title={row.executionIdLabel}>
                      {row.executionIdLabel}
                    </span>
                  </div>
                </div>
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
