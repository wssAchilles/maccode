import { useEffect, useRef } from 'react'

import { useReducedMotion } from './useReducedMotion'

type Options = {
  disabled?: boolean
  maxTilt?: number
  maxShift?: number
}

const FINE_POINTER_QUERY = '(hover: hover) and (pointer: fine)'

export function usePointerReactive<T extends HTMLElement>({
  disabled = false,
  maxTilt = 6,
  maxShift = 10,
}: Options = {}) {
  const ref = useRef<T | null>(null)
  const reducedMotion = useReducedMotion()

  useEffect(() => {
    const node = ref.current
    if (!node) {
      return
    }

    const hasFinePointer =
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia(FINE_POINTER_QUERY).matches

    if (disabled || reducedMotion || !hasFinePointer) {
      node.dataset.pointerMode = 'static'
      node.style.setProperty('--ms-x', '0px')
      node.style.setProperty('--ms-y', '0px')
      node.style.setProperty('--ms-rx', '0deg')
      node.style.setProperty('--ms-ry', '0deg')
      node.style.setProperty('--ms-px', '50%')
      node.style.setProperty('--ms-py', '50%')
      return
    }

    node.dataset.pointerMode = 'reactive'

    let rect = node.getBoundingClientRect()
    let frame = 0
    let targetX = 0
    let targetY = 0
    let targetRx = 0
    let targetRy = 0
    let targetPx = 50
    let targetPy = 50

    const commit = () => {
      frame = 0
      node.style.setProperty('--ms-x', `${targetX.toFixed(2)}px`)
      node.style.setProperty('--ms-y', `${targetY.toFixed(2)}px`)
      node.style.setProperty('--ms-rx', `${targetRx.toFixed(2)}deg`)
      node.style.setProperty('--ms-ry', `${targetRy.toFixed(2)}deg`)
      node.style.setProperty('--ms-px', `${targetPx.toFixed(2)}%`)
      node.style.setProperty('--ms-py', `${targetPy.toFixed(2)}%`)
    }

    const schedule = () => {
      if (frame) {
        return
      }
      frame = window.requestAnimationFrame(commit)
    }

    const handlePointerEnter = () => {
      rect = node.getBoundingClientRect()
      node.dataset.pointerState = 'active'
    }

    const handlePointerMove = (event: PointerEvent) => {
      if (!rect.width || !rect.height) {
        return
      }

      const px = (event.clientX - rect.left) / rect.width
      const py = (event.clientY - rect.top) / rect.height
      const nx = Math.max(-1, Math.min(1, px * 2 - 1))
      const ny = Math.max(-1, Math.min(1, py * 2 - 1))

      targetPx = Math.max(0, Math.min(100, px * 100))
      targetPy = Math.max(0, Math.min(100, py * 100))
      targetX = nx * maxShift
      targetY = ny * maxShift
      targetRx = ny * -maxTilt
      targetRy = nx * maxTilt
      schedule()
    }

    const reset = () => {
      node.dataset.pointerState = 'idle'
      targetX = 0
      targetY = 0
      targetRx = 0
      targetRy = 0
      targetPx = 50
      targetPy = 50
      schedule()
    }

    const handleWindowResize = () => {
      rect = node.getBoundingClientRect()
    }

    node.addEventListener('pointerenter', handlePointerEnter)
    node.addEventListener('pointermove', handlePointerMove)
    node.addEventListener('pointerleave', reset)
    window.addEventListener('resize', handleWindowResize)
    window.addEventListener('scroll', handleWindowResize, true)

    return () => {
      node.removeEventListener('pointerenter', handlePointerEnter)
      node.removeEventListener('pointermove', handlePointerMove)
      node.removeEventListener('pointerleave', reset)
      window.removeEventListener('resize', handleWindowResize)
      window.removeEventListener('scroll', handleWindowResize, true)
      window.cancelAnimationFrame(frame)
    }
  }, [disabled, maxShift, maxTilt, reducedMotion])

  return ref
}
