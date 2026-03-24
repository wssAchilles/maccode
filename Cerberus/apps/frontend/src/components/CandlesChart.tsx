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

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: '#121a30' },
        textColor: '#e5e7eb',
      },
      grid: {
        vertLines: { color: '#1f2937' },
        horzLines: { color: '#1f2937' },
      },
      width: containerRef.current.clientWidth,
      height: 340,
    })

    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#34d399',
      downColor: '#f87171',
      borderVisible: false,
      wickUpColor: '#34d399',
      wickDownColor: '#f87171',
    })

    seriesRef.current = series

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

  return <div ref={containerRef} className="w-full min-h-[340px]" aria-label="candles-chart" />
}
