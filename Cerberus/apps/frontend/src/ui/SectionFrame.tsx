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
    <GlassPanel className={cn('section-frame', className)} tone={tone}>
      <div className="section-frame-header">
        <div className="section-frame-copy">
          {eyebrow ? <p className="section-frame-eyebrow">{eyebrow}</p> : null}
          <h2 className="section-frame-title">{title}</h2>
          {description ? <p className="section-frame-description">{description}</p> : null}
        </div>
        {aside ? <div className="section-frame-aside">{aside}</div> : null}
      </div>
      <div className="section-frame-body">{children}</div>
    </GlassPanel>
  )
}
