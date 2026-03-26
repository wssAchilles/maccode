import { AnimatePresence, motion } from 'framer-motion'
import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'

import { cn } from '../lib/cn'

type Props = {
  title: string
  summary?: string
  children: ReactNode
  defaultOpen?: boolean
  className?: string
}

export function DiagnosticDrawer({ title, summary, children, defaultOpen = false, className }: Props) {
  const [open, setOpen] = useState(defaultOpen)

  useEffect(() => {
    if (defaultOpen) {
      setOpen(true)
    }
  }, [defaultOpen])

  return (
    <section className={cn('diagnostic-drawer', className)}>
      <button
        type="button"
        className="diagnostic-drawer-trigger"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        <div>
          <p className="diagnostic-drawer-title">{title}</p>
          {summary ? <p className="diagnostic-drawer-summary">{summary}</p> : null}
        </div>
        <span className={open ? 'diagnostic-drawer-chevron diagnostic-drawer-chevron-open' : 'diagnostic-drawer-chevron'}>
          {open ? '−' : '+'}
        </span>
      </button>
      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            className="diagnostic-drawer-content"
            initial={{ opacity: 0, height: 0, y: -6 }}
            animate={{ opacity: 1, height: 'auto', y: 0 }}
            exit={{ opacity: 0, height: 0, y: -6 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
          >
            {children}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </section>
  )
}
