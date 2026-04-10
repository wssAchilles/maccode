import type { ReactNode } from 'react'

import { cn } from '../lib/cn'
import { GlassPanel } from './GlassPanel'

type Props = {
  title: string
  description?: string
  eyebrow?: string
  backLabel: string
  onBack: () => void
  children: ReactNode
  aside?: ReactNode
  actions?: ReactNode
  layout?: 'single' | 'split'
  className?: string
  bodyClassName?: string
}

export function FocusedWorkspacePanel({
  title,
  description,
  eyebrow,
  backLabel,
  onBack,
  children,
  aside,
  actions,
  layout = aside ? 'split' : 'single',
  className,
  bodyClassName,
}: Props) {
  return (
    <div className={cn('fwp', className)} data-testid="focused-workspace-panel">
      <GlassPanel className="fwp-header" tone="subtle">
        <div className="fwp-copy">
          {eyebrow ? <p className="subtle-label">{eyebrow}</p> : null}
          <h2 className="fwp-title">{title}</h2>
          {description ? <p className="fwp-description">{description}</p> : null}
        </div>
        <div className="fwp-actions">
          {actions}
          <button type="button" className="soft-button" onClick={onBack}>
            {backLabel}
          </button>
        </div>
      </GlassPanel>
      <div className="fwp-layout" data-layout={layout}>
        <main className={cn('fwp-main', bodyClassName)}>{children}</main>
        {aside ? <aside className="fwp-aside">{aside}</aside> : null}
      </div>
    </div>
  )
}
