import { useEffect, useState } from 'react'

export function useRafPresenceTransition(trigger: string | number, duration = 420) {
  const [phase, setPhase] = useState<'idle' | 'entering'>('idle')

  useEffect(() => {
    let frame = 0
    let timeout = 0

    setPhase('entering')
    frame = window.requestAnimationFrame(() => {
      timeout = window.setTimeout(() => {
        setPhase('idle')
      }, duration)
    })

    return () => {
      window.cancelAnimationFrame(frame)
      window.clearTimeout(timeout)
    }
  }, [duration, trigger])

  return phase
}
