import { useEffect, useRef } from 'react'

import { useReducedMotion } from './useReducedMotion'

type Options = {
  disabled?: boolean
  once?: boolean
}

export function useRevealOnView<T extends HTMLElement>({
  disabled = false,
  once = true,
}: Options = {}) {
  const ref = useRef<T | null>(null)
  const reducedMotion = useReducedMotion()

  useEffect(() => {
    const node = ref.current
    if (!node) {
      return
    }

    if (disabled || reducedMotion) {
      node.dataset.reveal = 'visible'
      return
    }

    if (typeof IntersectionObserver === 'undefined') {
      node.dataset.reveal = 'visible'
      return
    }

    node.dataset.reveal = 'hidden'

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry) {
          return
        }

        if (entry.isIntersecting) {
          node.dataset.reveal = 'visible'
          if (once) {
            observer.disconnect()
          }
          return
        }

        if (!once) {
          node.dataset.reveal = 'hidden'
        }
      },
      {
        threshold: 0.18,
        rootMargin: '0px 0px -12% 0px',
      },
    )

    observer.observe(node)
    return () => observer.disconnect()
  }, [disabled, once, reducedMotion])

  return ref
}
