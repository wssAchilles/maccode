import type { CSSProperties } from 'react'

import { cn } from '../lib/cn'
import type { WorkspaceContextBandModel } from '../view-models/workbench'
import { accentVar } from './accent'

type Props = {
  model: WorkspaceContextBandModel
  className?: string
  compact?: boolean
}

export function TerminalBand({ model, className, compact = false }: Props) {
  const style = {
    '--pa': accentVar(model.accent ?? 'cyan'),
  } as CSSProperties

  return (
    <div className={cn('tb', compact && 'tb-compact', className)} style={style}>
      <div className="tb-copy">
        <p className="subtle-label">{model.eyebrow}</p>
        <p className="tb-title">{model.title}</p>
        <p className="panel-caption">{model.hint}</p>
      </div>
      <div className="tb-grid">
        {model.items.map((item) => (
          <div key={item.id} className="tb-item">
            <p className="subtle-label">{item.label}</p>
            <p
              className={
                item.tone === 'positive'
                  ? 'tb-value dl-value-positive'
                  : item.tone === 'negative'
                    ? 'tb-value dl-value-negative'
                    : item.tone === 'accent'
                      ? 'tb-value dl-value-accent'
                      : 'tb-value'
              }
            >
              {item.value}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
