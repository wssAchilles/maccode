import type { CSSProperties, HTMLAttributes, ReactNode } from 'react'

import { cn } from '../lib/cn'
import { useRevealOnView } from './motion/useRevealOnView'

type Props = Omit<HTMLAttributes<HTMLDivElement>, 'children'> & {
  children: ReactNode
  disabled?: boolean
  revealIndex?: number
  once?: boolean
}

export function RevealGroup({
  children,
  className,
  disabled = false,
  revealIndex,
  once = true,
  style,
  ...props
}: Props) {
  const ref = useRevealOnView<HTMLDivElement>({ disabled, once })

  return (
    <div
      ref={ref}
      className={cn('rg', className)}
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
