import { cn } from '../lib/cn'
import type { WorkspaceSpotlightModel } from '../view-models/workbench'
import { GlassPanel } from './GlassPanel'
import { MotionSurface } from './MotionSurface'
import { RevealGroup } from './RevealGroup'

type Props = {
  model: WorkspaceSpotlightModel
  compact?: boolean
  className?: string
}

export function WorkspaceSpotlight({ model, compact = false, className }: Props) {
  return (
    <RevealGroup className={cn('sp-shell', className)}>
      <MotionSurface mode={compact ? 'panel' : 'spotlight'}>
        <GlassPanel className={cn(compact ? 'sp sp-compact' : 'sp')} tone="subtle">
          <div className="sp-head">
            <div className="sf-copy">
              {model.postureLabel ? <p className="subtle-label">{model.postureLabel}</p> : null}
              <p className="sp-summary">{model.summary}</p>
              {model.hint ? <p className="panel-caption">{model.hint}</p> : null}
            </div>
            {model.chips.length > 0 ? (
              <div className="ws-actions" aria-label="workspace-spotlight-chips">
                {model.chips.map((chip, index) => (
                  <span key={`${chip}-${index}`} className="account-pill">
                    {chip}
                  </span>
                ))}
              </div>
            ) : null}
          </div>

          <div className="obs-grid">
            {model.metrics.map((metric) => (
              <div key={metric.id} className="obs-card" data-priority={metric.visualPriority ?? 'secondary'}>
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
            ))}
          </div>
        </GlassPanel>
      </MotionSurface>
    </RevealGroup>
  )
}
