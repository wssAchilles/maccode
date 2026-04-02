import type { CSSProperties, HTMLAttributes, ReactNode } from 'react'

import { cn } from '../lib/cn'
import { usePointerReactive } from './motion/usePointerReactive'

type Props = Omit<HTMLAttributes<HTMLDivElement>, 'children'> & {
  children: ReactNode
  mode?: 'panel' | 'button' | 'metric' | 'spotlight'
  disabled?: boolean
  reactive?: boolean
  revealIndex?: number
}

export function MotionSurface({
  children,
  className,
  mode = 'panel',
  disabled = false,
  reactive,
  revealIndex,
  style,
  ...props
}: Props) {
  const shouldReact = reactive ?? (mode === 'button' || mode === 'spotlight')
  const ref = usePointerReactive<HTMLDivElement>({
    disabled: disabled || !shouldReact,
    maxShift: mode === 'button' ? 8 : mode === 'metric' ? 6 : mode === 'spotlight' ? 12 : 9,
    maxTilt: mode === 'button' ? 5 : mode === 'metric' ? 4 : mode === 'spotlight' ? 7 : 6,
  })

  return (
    <div
      ref={ref}
      className={cn('ms', `ms-${mode}`, className)}
      data-motion-disabled={disabled ? 'true' : 'false'}
      data-motion-reactive={shouldReact ? 'true' : 'false'}
      data-motion-mode={mode}
      style={{
        ...(style as CSSProperties | undefined),
        '--reveal-index': revealIndex === undefined ? undefined : String(revealIndex),
      } as CSSProperties}
      {...props}
    >
      {children}
    </div>
  )
}
