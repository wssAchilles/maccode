import { useEffect, useRef } from 'react'

import { cn } from '../lib/cn'
import { useReducedMotion } from './motion/useReducedMotion'
import type { AccentTone } from './accent'

type Props = {
  accent?: AccentTone
  className?: string
  intensity?: 'hero' | 'stage'
}

const ACCENT_RGB: Record<AccentTone, [number, number, number]> = {
  teal: [45, 212, 191],
  cyan: [56, 189, 248],
  amber: [245, 158, 11],
}

export function MotionBackdrop({
  accent = 'teal',
  className,
  intensity = 'hero',
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const reducedMotion = useReducedMotion()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || reducedMotion || typeof window === 'undefined') {
      return
    }

    const parent = canvas.parentElement
    if (!parent) {
      return
    }

    const pointerQuery = window.matchMedia('(hover: hover) and (pointer: fine)')
    if (!pointerQuery.matches) {
      return
    }

    const ctx = canvas.getContext('2d', { alpha: true })
    if (!ctx) {
      return
    }

    const [r, g, b] = ACCENT_RGB[accent]
    const secondary = accent === 'amber' ? ACCENT_RGB.cyan : ACCENT_RGB.teal

    let width = 0
    let height = 0
    let frame = 0
    let lastPaint = 0
    let pointerX = 0.5
    let pointerY = 0.5
    let currentX = 0.5
    let currentY = 0.5
    let visible = document.visibilityState === 'visible'
    let inViewport = true
    const maxVisualHeight =
      intensity === 'stage'
        ? Math.max(520, Math.min(window.innerHeight * 1.18, 860))
        : Number.POSITIVE_INFINITY
    const targetFrameInterval = intensity === 'stage' ? 1000 / 18 : 1000 / 28

    const resize = () => {
      const rect = parent.getBoundingClientRect()
      width = Math.max(1, Math.floor(rect.width))
      height = Math.max(1, Math.floor(Math.min(rect.height, maxVisualHeight)))
      const scale = intensity === 'stage' ? 0.85 : Math.min(window.devicePixelRatio || 1, 1.2)
      canvas.width = Math.floor(width * scale)
      canvas.height = Math.floor(height * scale)
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.setTransform(scale, 0, 0, scale, 0, 0)
    }

    const drawOrb = (
      x: number,
      y: number,
      radius: number,
      color: [number, number, number],
      alpha: number,
    ) => {
      const gradient = ctx.createRadialGradient(x, y, radius * 0.12, x, y, radius)
      gradient.addColorStop(0, `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${alpha})`)
      gradient.addColorStop(0.55, `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${alpha * 0.42})`)
      gradient.addColorStop(1, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0)`)
      ctx.fillStyle = gradient
      ctx.beginPath()
      ctx.arc(x, y, radius, 0, Math.PI * 2)
      ctx.fill()
    }

    const render = (time: number) => {
      if (!visible || !inViewport) {
        frame = window.requestAnimationFrame(render)
        return
      }

      if (time - lastPaint < targetFrameInterval) {
        frame = window.requestAnimationFrame(render)
        return
      }
      lastPaint = time

      ctx.clearRect(0, 0, width, height)

      currentX += (pointerX - currentX) * 0.045
      currentY += (pointerY - currentY) * 0.045

      const t = time * 0.00028
      const baseRadius = Math.max(width, height) * (intensity === 'hero' ? 0.32 : 0.24)
      const driftX = (currentX - 0.5) * width * 0.16
      const driftY = (currentY - 0.5) * height * 0.18

      ctx.save()
      ctx.filter = intensity === 'hero' ? 'blur(8px)' : 'blur(8px)'

      drawOrb(
        width * 0.22 + Math.sin(t * 1.8) * width * 0.08 + driftX,
        height * 0.34 + Math.cos(t * 1.4) * height * 0.08 + driftY,
        baseRadius,
        [r, g, b],
        intensity === 'hero' ? 0.2 : 0.14,
      )
      drawOrb(
        width * 0.78 + Math.cos(t * 1.2) * width * 0.07 - driftX * 0.7,
        height * 0.28 + Math.sin(t * 1.6) * height * 0.06 - driftY * 0.6,
        baseRadius * 0.84,
        secondary,
        intensity === 'hero' ? 0.14 : 0.1,
      )
      drawOrb(
        width * 0.56 + Math.sin(t) * width * 0.04,
        height * 0.74 + Math.cos(t * 1.25) * height * 0.05,
        baseRadius * 0.56,
        [255, 255, 255],
        intensity === 'hero' ? 0.18 : 0.1,
      )

      ctx.restore()

      ctx.save()
      ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${intensity === 'hero' ? 0.16 : 0.1})`
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(0, height * (0.2 + currentY * 0.1))
      ctx.bezierCurveTo(
        width * 0.28,
        height * (0.12 + currentY * 0.08),
        width * 0.62,
        height * (0.34 + currentX * 0.04),
        width,
        height * (0.24 + currentY * 0.1),
      )
      ctx.stroke()
      ctx.restore()

      frame = window.requestAnimationFrame(render)
    }

    const handlePointerMove = (event: PointerEvent) => {
      const rect = parent.getBoundingClientRect()
      if (!rect.width || !rect.height) {
        return
      }
      pointerX = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width))
      pointerY = Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height))
    }

    const handlePointerLeave = () => {
      pointerX = 0.5
      pointerY = 0.5
    }

    const handleVisibility = () => {
      visible = document.visibilityState === 'visible'
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        inViewport = entry?.isIntersecting ?? true
      },
      {
        rootMargin: '160px 0px 160px 0px',
        threshold: 0,
      },
    )

    resize()
    frame = window.requestAnimationFrame(render)

    const resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(parent)
    observer.observe(canvas)
    document.addEventListener('visibilitychange', handleVisibility)
    if (intensity === 'hero') {
      parent.addEventListener('pointermove', handlePointerMove)
      parent.addEventListener('pointerleave', handlePointerLeave)
    }

    return () => {
      observer.disconnect()
      resizeObserver.disconnect()
      document.removeEventListener('visibilitychange', handleVisibility)
      if (intensity === 'hero') {
        parent.removeEventListener('pointermove', handlePointerMove)
        parent.removeEventListener('pointerleave', handlePointerLeave)
      }
      window.cancelAnimationFrame(frame)
    }
  }, [accent, intensity, reducedMotion])

  return <canvas ref={canvasRef} className={cn('mb', `mb-${intensity}`, className)} aria-hidden="true" />
}
