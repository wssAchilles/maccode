import {
  CandlestickSeries,
  createChart,
  type ISeriesApi,
  type UTCTimestamp,
} from 'lightweight-charts'
import { useEffect, useRef } from 'react'

import type { Candle } from '../types/contracts'

type Props = {
  candles: Candle[]
}

export function CandlesChart({ candles }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)

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

    seriesRef.current = series
    chart.timeScale().fitContent()

    const resizeObserver = new ResizeObserver(() => {
      chart.applyOptions({ width: containerRef.current?.clientWidth ?? 680 })
    })
    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
      chart.remove()
    }
  }, [])

  useEffect(() => {
    if (!seriesRef.current || candles.length === 0) {
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
  }, [candles])

  return <div ref={containerRef} className="chart-frame" aria-label="candles-chart" />
}
