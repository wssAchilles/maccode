import type { ReactNode } from 'react'

import { cn } from '../lib/cn'

type Props = {
  title: string
  children: ReactNode
  tone?: 'info' | 'warning' | 'danger'
  className?: string
}

const TONE_CLASS: Record<NonNullable<Props['tone']>, string> = {
  info: 'inline-alert inline-alert-info',
  warning: 'inline-alert inline-alert-warning',
  danger: 'inline-alert inline-alert-danger',
}

export function InlineAlert({ title, children, tone = 'info', className }: Props) {
  return (
    <div className={cn(TONE_CLASS[tone], className)} role={tone === 'danger' ? 'alert' : 'status'}>
      <p className="inline-alert-title">{title}</p>
      <div className="inline-alert-body">{children}</div>
    </div>
  )
}
