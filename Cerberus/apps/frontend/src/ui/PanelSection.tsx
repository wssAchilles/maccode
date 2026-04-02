import type { ReactNode } from 'react'

import { cn } from '../lib/cn'

type Props = {
  eyebrow?: string
  title: string
  hint?: string
  aside?: ReactNode
  className?: string
  bodyClassName?: string
  children?: ReactNode
}

export function PanelSection({
  eyebrow,
  title,
  hint,
  aside,
  className,
  bodyClassName,
  children,
}: Props) {
  return (
    <section className={cn('psx', className)}>
      <div className="psx-head">
        <div className="psx-copy">
          {eyebrow ? <p className="subtle-label">{eyebrow}</p> : null}
          <p className="psx-title">{title}</p>
          {hint ? <p className="psx-hint">{hint}</p> : null}
        </div>
        {aside ? <div className="psx-aside">{aside}</div> : null}
      </div>
      {children ? <div className={cn('psx-body', bodyClassName)}>{children}</div> : null}
    </section>
  )
}
