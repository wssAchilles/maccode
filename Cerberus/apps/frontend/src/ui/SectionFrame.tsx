import type { ReactNode } from 'react'

import { cn } from '../lib/cn'
import { GlassPanel } from './GlassPanel'

type Props = {
  title: string
  description?: string
  eyebrow?: string
  aside?: ReactNode
  children: ReactNode
  className?: string
  tone?: 'default' | 'hero' | 'subtle'
}

export function SectionFrame({
  title,
  description,
  eyebrow,
  aside,
  children,
  className,
  tone = 'default',
}: Props) {
  return (
    <GlassPanel className={cn('sf', className)} tone={tone}>
      <div className="sf-header">
        <div className="sf-copy">
          {eyebrow ? <p className="sf-eyebrow">{eyebrow}</p> : null}
          <h2 className="sf-title">{title}</h2>
          {description ? <p className="sf-description">{description}</p> : null}
        </div>
        {aside ? <div className="sf-aside">{aside}</div> : null}
      </div>
      <div className="sf-body">{children}</div>
    </GlassPanel>
  )
}
