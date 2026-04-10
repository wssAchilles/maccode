import { useId } from 'react'
import type { LoadState } from '../types/contracts'
import { cn } from '../lib/cn'
import { GlassPanel } from './GlassPanel'
import { MotionSurface } from './MotionSurface'
import { RevealGroup } from './RevealGroup'
import { StatusPill } from './StatusPill'

export type SubpageLauncherItem = {
  id: string
  title: string
  description: string
  cta: string
  state?: LoadState | 'active' | 'success'
  stateLabel?: string
}

type Props = {
  title: string
  description?: string
  items: SubpageLauncherItem[]
  onSelect: (id: string) => void
  activeId?: string
  className?: string
}

export function SubpageLauncher({ title, description, items, onSelect, activeId, className }: Props) {
  const titleId = useId()

  return (
    <section
      className={cn('spl', className)}
      data-count={items.length}
      data-testid="subpage-launcher"
      aria-labelledby={titleId}
    >
      <div className="spl-head">
        <div className="spl-copy">
          <p className="subtle-label" id={titleId}>
            {title}
          </p>
          {description ? <p className="spl-description">{description}</p> : null}
        </div>
      </div>
      <div className="spl-grid">
        {items.map((item, index) => (
          <RevealGroup key={item.id} revealIndex={index} className="spl-shell">
            <MotionSurface className="spl-surface" mode="button">
              <button
                type="button"
                className={cn('spl-button', activeId === item.id && 'spl-button-active')}
                onClick={() => onSelect(item.id)}
              >
                <GlassPanel className="spl-card" tone="subtle">
                  <div className="spl-card-head">
                    <div className="spl-card-copy">
                      <p className="spl-title">{item.title}</p>
                      <p className="spl-card-description">{item.description}</p>
                    </div>
                    {item.state && item.stateLabel ? (
                      <StatusPill state={item.state} label={item.stateLabel} compact />
                    ) : null}
                  </div>
                  <span className="spl-cta">{item.cta}</span>
                </GlassPanel>
              </button>
            </MotionSurface>
          </RevealGroup>
        ))}
      </div>
    </section>
  )
}
