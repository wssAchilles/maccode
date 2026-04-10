import type { CSSProperties, ReactNode } from 'react'

import { cn } from '../lib/cn'
import { accentVar, type AccentTone } from './accent'
import { GlassPanel } from './GlassPanel'
import { MotionSurface } from './MotionSurface'
import { RevealGroup } from './RevealGroup'

type Props = {
  title: string
  description?: string
  descriptionMode?: 'visible' | 'srOnly' | 'hidden'
  eyebrow?: string
  aside?: ReactNode
  children: ReactNode
  className?: string
  bodyClassName?: string
  compactHeader?: boolean
  tone?: 'default' | 'hero' | 'subtle'
  accent?: AccentTone
  stage?: 'hero' | 'feature' | 'operator' | 'inspector' | 'tail'
}

export function SectionFrame({
  title,
  description,
  descriptionMode = 'visible',
  eyebrow,
  aside,
  children,
  className,
  bodyClassName,
  compactHeader = false,
  tone = 'default',
  accent = 'teal',
  stage = 'feature',
}: Props) {
  const style = {
    '--pa': accentVar(accent),
  } as CSSProperties

  return (
    <RevealGroup className={cn('sf-shell', className)} data-stage={stage} style={style}>
      <MotionSurface className="sf-surface" mode={tone === 'hero' ? 'spotlight' : 'panel'} data-stage={stage}>
        <GlassPanel className="sf" tone={tone} data-stage={stage}>
          <div className={cn('sf-header', compactHeader && 'sf-header-compact')}>
            <div className="sf-copy">
              {eyebrow ? <p className="sf-eyebrow">{eyebrow}</p> : null}
              <h2 className="sf-title">{title}</h2>
              {description && descriptionMode === 'visible' ? <p className="sf-description">{description}</p> : null}
              {description && descriptionMode === 'srOnly' ? <p className="sr-only">{description}</p> : null}
            </div>
            {aside ? <div className="sf-aside">{aside}</div> : null}
          </div>
          <div className={cn('sf-body', bodyClassName)}>{children}</div>
        </GlassPanel>
      </MotionSurface>
    </RevealGroup>
  )
}
