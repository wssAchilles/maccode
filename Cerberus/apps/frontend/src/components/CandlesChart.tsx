import {
  CandlestickSeries,
  createSeriesMarkers,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts'
import { useEffect, useRef } from 'react'

import type { Candle } from '../types/contracts'
import type { MarketChartMarkerModel } from '../features/market/view-models'

type Props = {
  candles: Candle[]
  markers?: MarketChartMarkerModel[]
}

export function CandlesChart({ candles, markers = [] }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const markersRef = useRef<ReturnType<typeof createSeriesMarkers<Time>> | null>(null)

  useEffect(() => {
    if (!containerRef.current) {
      return
    }

    const styles = getComputedStyle(document.documentElement)
    const chartText = styles.getPropertyValue('--color-chart-text').trim() || '#536275'
    const chartGrid = styles.getPropertyValue('--color-chart-grid').trim() || 'rgba(120, 136, 157, 0.14)'
    const chartAxis = styles.getPropertyValue('--color-chart-axis').trim() || 'rgba(103, 120, 145, 0.22)'
    const chartCrosshair = styles.getPropertyValue('--color-chart-crosshair').trim() || 'rgba(53, 94, 147, 0.26)'
    const upColor = styles.getPropertyValue('--color-success').trim() || '#15803d'
    const downColor = styles.getPropertyValue('--color-danger').trim() || '#b91c1c'

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: 'transparent' },
        textColor: chartText,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: chartGrid },
        horzLines: { color: chartGrid },
      },
      rightPriceScale: {
        borderColor: chartAxis,
      },
      timeScale: {
        borderColor: chartAxis,
      },
      crosshair: {
        vertLine: { color: chartCrosshair },
        horzLine: { color: chartCrosshair },
      },
      width: containerRef.current.clientWidth,
      height: 360,
    })

    const series = chart.addSeries(CandlestickSeries, {
      upColor,
      downColor,
      borderVisible: false,
      wickUpColor: upColor,
      wickDownColor: downColor,
    })

    chartRef.current = chart
    seriesRef.current = series
    markersRef.current = createSeriesMarkers(series, [])
    chart.timeScale().fitContent()

    const resizeObserver = new ResizeObserver(() => {
      chart.applyOptions({ width: containerRef.current?.clientWidth ?? 680 })
    })
    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
      chartRef.current = null
      seriesRef.current = null
      markersRef.current = null
      chart.remove()
    }
  }, [])

  useEffect(() => {
    if (!seriesRef.current) {
      return
    }

    seriesRef.current.setData(
      candles.map((k) => ({
        time: Math.floor(k[0] / 1000) as UTCTimestamp,
        open: Number(k[1]),
        high: Number(k[2]),
        low: Number(k[3]),
        close: Number(k[4]),
      })),
    )

    if (candles.length > 0) {
      chartRef.current?.timeScale().fitContent()
    }
  }, [candles])

  useEffect(() => {
    if (!markersRef.current) {
      return
    }
    const markerPayload: SeriesMarker<Time>[] = markers.map((item) => ({
      time: Math.floor(item.time / 1000) as UTCTimestamp,
      position:
        item.phase === 'fill'
          ? 'belowBar'
          : item.phase === 'rejected'
            ? 'aboveBar'
            : 'inBar',
      shape:
        item.phase === 'fill'
          ? 'arrowUp'
          : item.phase === 'rejected'
            ? 'arrowDown'
            : 'circle',
      color:
        item.tone === 'positive'
          ? '#15803d'
          : item.tone === 'negative'
            ? '#b91c1c'
            : item.tone === 'accent'
              ? '#0369a1'
              : '#64748b',
      text: item.label,
    }))
    markersRef.current.setMarkers(markerPayload)
  }, [markers])

  return <div ref={containerRef} className="chart-frame" aria-label="candles-chart" />
}
