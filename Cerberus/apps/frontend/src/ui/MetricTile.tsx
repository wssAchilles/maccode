import type { ReactNode } from 'react'

import { cn } from '../lib/cn'
import { GlassPanel } from './GlassPanel'
import { MotionSurface } from './MotionSurface'
import { RevealGroup } from './RevealGroup'

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
  positive: 'met-positive',
  negative: 'met-negative',
  accent: 'met-accent',
}

export function MetricTile({ label, value, hint, caption, tone = 'default', className }: Props) {
  return (
    <RevealGroup className={className}>
      <MotionSurface mode="metric">
        <GlassPanel className={cn('metric-tile', TONE_CLASS[tone])} tone="subtle">
          <p className="met-label">{label}</p>
          <p className="met-value">{value}</p>
          {hint ? <p className="met-hint">{hint}</p> : null}
          {caption ? <div className="met-caption">{caption}</div> : null}
        </GlassPanel>
      </MotionSurface>
    </RevealGroup>
  )
}
