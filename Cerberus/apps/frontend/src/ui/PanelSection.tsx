import type { ReactNode } from 'react'

import { cn } from '../lib/cn'

type Props = {
  eyebrow?: string
  title: string
  hint?: string
  hideEyebrow?: boolean
  aside?: ReactNode
  className?: string
  bodyClassName?: string
  children?: ReactNode
  compact?: boolean
}

export function PanelSection({
  eyebrow,
  title,
  hint,
  hideEyebrow = false,
  aside,
  className,
  bodyClassName,
  children,
  compact = false,
}: Props) {
  return (
    <section className={cn('psx', compact && 'psx-compact', className)}>
      <div className="psx-head">
        <div className="psx-copy">
          {eyebrow && !hideEyebrow ? <p className="subtle-label">{eyebrow}</p> : null}
          <p className="psx-title">{title}</p>
          {hint ? <p className="psx-hint">{hint}</p> : null}
        </div>
        {aside ? <div className="psx-aside">{aside}</div> : null}
      </div>
      {children ? <div className={cn('psx-body', bodyClassName)}>{children}</div> : null}
    </section>
  )
}
