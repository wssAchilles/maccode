import type { ReactNode } from 'react'

import { cn } from '../lib/cn'
import { GlassPanel } from './GlassPanel'

type Props = {
  label: string
  value: string
  hint?: string
  caption?: ReactNode
  tone?: 'default' | 'positive' | 'negative' | 'accent'
  className?: string
}

const TONE_CLASS: Record<NonNullable<Props['tone']>, string> = {
  default: '',
  positive: 'metric-tile-positive',
  negative: 'metric-tile-negative',
  accent: 'metric-tile-accent',
}

export function MetricTile({ label, value, hint, caption, tone = 'default', className }: Props) {
  return (
    <GlassPanel className={cn('metric-tile', TONE_CLASS[tone], className)} tone="subtle">
      <p className="metric-tile-label">{label}</p>
      <p className="metric-tile-value">{value}</p>
      {hint ? <p className="metric-tile-hint">{hint}</p> : null}
      {caption ? <div className="metric-tile-caption">{caption}</div> : null}
    </GlassPanel>
  )
}
