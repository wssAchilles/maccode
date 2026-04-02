import type { CSSProperties } from 'react'

import { cn } from '../lib/cn'
import type { WorkspaceSpotlightModel } from '../view-models/workbench'
import { accentVar } from './accent'
import { GlassPanel } from './GlassPanel'
import { MotionSurface } from './MotionSurface'
import { RevealGroup } from './RevealGroup'

type Props = {
  model: WorkspaceSpotlightModel
  compact?: boolean
  className?: string
}

export function WorkspaceSpotlight({ model, compact = false, className }: Props) {
  const accent = model.accent ?? 'teal'
  const style = {
    '--pa': accentVar(accent),
  } as CSSProperties

  return (
    <RevealGroup className={cn('sp-shell', className)} style={style}>
      <MotionSurface className="sp-surface" mode={compact ? 'panel' : 'spotlight'}>
        <GlassPanel className={compact ? 'sp sp-compact' : 'sp'} tone="subtle">
          <div className="sp-head">
            <div className="sf-copy">
              {model.postureLabel ? <p className="subtle-label">{model.postureLabel}</p> : null}
              <p className="sp-summary">{model.summary}</p>
              {model.hint ? <p className="panel-caption">{model.hint}</p> : null}
            </div>
            {model.chips.length > 0 ? (
              <div className="sp-chip-row" aria-label="workspace-spotlight-chips">
                {model.chips.map((chip, index) => (
                  <span key={`${chip}-${index}`} className="account-pill">
                    {chip}
                  </span>
                ))}
              </div>
            ) : null}
          </div>

          <div className="obs-grid">
            {model.metrics.map((metric, index) => (
              <RevealGroup key={metric.id} revealIndex={index + 1}>
                <MotionSurface className="obs-surface" mode="metric">
                  <div className="obs-card" data-priority={metric.visualPriority ?? 'secondary'}>
                    <p className="subtle-label">{metric.label}</p>
                    <p
                      className={cn(
                        'obs-value',
                        metric.tone === 'positive'
                          ? 'dl-value-positive'
                          : metric.tone === 'negative'
                            ? 'dl-value-negative'
                            : metric.tone === 'accent'
                              ? 'dl-value-accent'
                              : '',
                      )}
                    >
                      {metric.value}
                    </p>
                    {metric.hint ? <p className="panel-caption">{metric.hint}</p> : null}
                  </div>
                </MotionSurface>
              </RevealGroup>
            ))}
          </div>
        </GlassPanel>
      </MotionSurface>
    </RevealGroup>
  )
}
