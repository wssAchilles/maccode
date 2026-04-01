import type { LoadState } from '../types/contracts'
import { cn } from '../lib/cn'

type Props = {
  state: LoadState | 'active' | 'success'
  label: string
  compact?: boolean
}

const STATE_CLASS: Record<Props['state'], string> = {
  idle: 'stp',
  loading: 'stp stpl',
  ready: 'stp stpr',
  degraded: 'stp stpd',
  error: 'stp stpe',
  active: 'stp stpl',
  success: 'stp stpr',
}

export function StatusPill({ state, label, compact = false }: Props) {
  return <span className={cn(STATE_CLASS[state], compact ? 'stpc' : '')}>{label}</span>
}
