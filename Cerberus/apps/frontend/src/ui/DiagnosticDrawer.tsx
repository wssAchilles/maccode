import type { ReactNode } from 'react'
import { useEffect, useId, useState } from 'react'

import { cn } from '../lib/cn'

type Props = {
  title: string
  summary?: string
  children: ReactNode
  defaultOpen?: boolean
  className?: string
  contentClassName?: string
  testId?: string
}

export function DiagnosticDrawer({
  title,
  summary,
  children,
  defaultOpen = false,
  className,
  contentClassName,
  testId,
}: Props) {
  const [open, setOpen] = useState(defaultOpen)
  const contentId = useId()

  useEffect(() => {
    if (defaultOpen) {
      setOpen(true)
    }
  }, [defaultOpen])

  return (
    <section className={cn('dd', className)} data-testid={testId}>
      <button
        type="button"
        className="dd-trigger"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={contentId}
        data-testid={testId ? `${testId}-trigger` : undefined}
      >
        <div>
          <p className="dd-title">{title}</p>
          {summary ? <p className="dd-summary">{summary}</p> : null}
        </div>
        <span className={open ? 'dd-chevron dd-chevron-open' : 'dd-chevron'}>
          {open ? '−' : '+'}
        </span>
      </button>
      {open ? (
        <div
          id={contentId}
          className={cn('dd-content', contentClassName)}
          data-testid={testId ? `${testId}-content` : undefined}
        >
          {children}
        </div>
      ) : null}
    </section>
  )
}
