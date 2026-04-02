import {
  CandlestickSeries,
  createSeriesMarkers,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type Time,
} from 'lightweight-charts'
import { useEffect, useEffectEvent, useRef } from 'react'

import {
  type MarketChartMarkersModel,
  type MarketChartSeriesModel,
  getMarketChartReplayStartIndex,
  isSameMarketChartCandle,
} from '../features/market/view-models'

type Props = {
  series: MarketChartSeriesModel
  markers?: MarketChartMarkersModel
}

export function CandlesChart({ series, markers }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const markersRef = useRef<ReturnType<typeof createSeriesMarkers<Time>> | null>(null)
  const widthRef = useRef(0)
  const resizeRafRef = useRef<number | null>(null)
  const markerSignatureRef = useRef('')
  const dataRef = useRef<MarketChartSeriesModel>({
    points: [],
    prefixHashes: new Uint32Array(0),
    firstTime: undefined,
    lastTime: undefined,
  })

  const applyChartWidth = useEffectEvent(() => {
    const nextWidth = containerRef.current?.clientWidth ?? 680
    if (!chartRef.current || nextWidth <= 0 || nextWidth === widthRef.current) {
      return
    }
    widthRef.current = nextWidth
    chartRef.current.applyOptions({ width: nextWidth })
  })

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
    widthRef.current = containerRef.current.clientWidth
    chart.timeScale().fitContent()

    const resizeObserver = new ResizeObserver(() => {
      if (resizeRafRef.current !== null) {
        return
      }
      resizeRafRef.current = window.requestAnimationFrame(() => {
        resizeRafRef.current = null
        applyChartWidth()
      })
    })
    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
      if (resizeRafRef.current !== null) {
        window.cancelAnimationFrame(resizeRafRef.current)
      }
      chartRef.current = null
      seriesRef.current = null
      markersRef.current = null
      widthRef.current = 0
      resizeRafRef.current = null
      markerSignatureRef.current = ''
      dataRef.current = {
        points: [],
        prefixHashes: new Uint32Array(0),
        firstTime: undefined,
        lastTime: undefined,
      }
      chart.remove()
    }
  }, [])

  useEffect(() => {
    if (!seriesRef.current) {
      return
    }

    const previous = dataRef.current
    const nextPoints = series.points

    if (nextPoints.length === 0) {
      if (previous.points.length > 0) {
        seriesRef.current.setData([])
        dataRef.current = series
      }
      return
    }

    const startIndex = getMarketChartReplayStartIndex(previous, series)
    if (startIndex < 0) {
      seriesRef.current.setData(nextPoints)
      dataRef.current = series
      chartRef.current?.timeScale().fitContent()
      return
    }

    for (let index = startIndex; index < nextPoints.length; index += 1) {
      if (isSameMarketChartCandle(previous.points[index], nextPoints[index])) {
        continue
      }
      seriesRef.current.update(nextPoints[index])
    }

    dataRef.current = series
  }, [series])

  useEffect(() => {
    if (!markersRef.current) {
      return
    }

    const nextSignature = markers?.signature ?? ''

    if (nextSignature === markerSignatureRef.current) {
      return
    }

    markerSignatureRef.current = nextSignature
    markersRef.current.setMarkers(markers?.items ?? [])
  }, [markers])

  return <div ref={containerRef} className="chart-frame" aria-label="candles-chart" />
}
