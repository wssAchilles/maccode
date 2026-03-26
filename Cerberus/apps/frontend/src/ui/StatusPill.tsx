import type { LoadState } from '../types/contracts'
import { cn } from '../lib/cn'

type Props = {
  state: LoadState | 'active' | 'success'
  label: string
  compact?: boolean
}

const STATE_CLASS: Record<Props['state'], string> = {
  idle: 'status-pill',
  loading: 'status-pill status-pill-loading',
  ready: 'status-pill status-pill-ready',
  degraded: 'status-pill status-pill-degraded',
  error: 'status-pill status-pill-error',
  active: 'status-pill status-pill-loading',
  success: 'status-pill status-pill-ready',
}

export function StatusPill({ state, label, compact = false }: Props) {
  return <span className={cn(STATE_CLASS[state], compact ? 'status-pill-compact' : '')}>{label}</span>
}
