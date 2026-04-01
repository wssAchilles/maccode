import {
  CandlestickSeries,
  createSeriesMarkers,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type Time,
} from 'lightweight-charts'
import { useEffect, useRef } from 'react'

import type { MarketChartCandleModel, MarketChartMarkerModel } from '../features/market/view-models'

type Props = {
  series: MarketChartCandleModel[]
  markers?: MarketChartMarkerModel[]
}

function sameCandle(left: MarketChartCandleModel | undefined, right: MarketChartCandleModel | undefined): boolean {
  return (
    left?.time === right?.time &&
    left?.open === right?.open &&
    left?.high === right?.high &&
    left?.low === right?.low &&
    left?.close === right?.close
  )
}

function canIncrementallyReplay(previous: MarketChartCandleModel[], next: MarketChartCandleModel[]): boolean {
  if (previous.length === 0 || next.length === 0 || next.length < previous.length) {
    return false
  }

  if (previous[0]?.time !== next[0]?.time) {
    return false
  }

  const sharedCount = previous.length - 1
  for (let index = 0; index < sharedCount; index += 1) {
    if (!sameCandle(previous[index], next[index])) {
      return false
    }
  }

  return true
}

export function CandlesChart({ series, markers = [] }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const markersRef = useRef<ReturnType<typeof createSeriesMarkers<Time>> | null>(null)
  const dataRef = useRef<MarketChartCandleModel[]>([])

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
      dataRef.current = []
      chart.remove()
    }
  }, [])

  useEffect(() => {
    if (!seriesRef.current) {
      return
    }

    const previous = dataRef.current

    if (series.length === 0) {
      if (previous.length > 0) {
        seriesRef.current.setData([])
        dataRef.current = []
      }
      return
    }

    if (!canIncrementallyReplay(previous, series)) {
      seriesRef.current.setData(series)
      dataRef.current = series
      chartRef.current?.timeScale().fitContent()
      return
    }

    const startIndex = Math.max(0, previous.length - 1)
    for (let index = startIndex; index < series.length; index += 1) {
      if (sameCandle(previous[index], series[index])) {
        continue
      }
      seriesRef.current.update(series[index])
    }

    dataRef.current = series
  }, [series])

  useEffect(() => {
    if (!markersRef.current) {
      return
    }

    markersRef.current.setMarkers(markers)
  }, [markers])

  return <div ref={containerRef} className="chart-frame" aria-label="candles-chart" />
}
