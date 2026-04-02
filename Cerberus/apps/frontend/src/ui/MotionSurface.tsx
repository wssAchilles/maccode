import type { CSSProperties, HTMLAttributes, ReactNode } from 'react'

import { cn } from '../lib/cn'

type Props = Omit<HTMLAttributes<HTMLDivElement>, 'children'> & {
  children: ReactNode
  mode?: 'panel' | 'button' | 'metric' | 'spotlight'
  disabled?: boolean
  revealIndex?: number
}

export function MotionSurface({
  children,
  className,
  mode = 'panel',
  disabled = false,
  revealIndex,
  style,
  ...props
}: Props) {
  return (
    <div
      className={cn('ms', `ms-${mode}`, className)}
      data-motion-disabled={disabled ? 'true' : 'false'}
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
