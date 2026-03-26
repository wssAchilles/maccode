import type { ComponentPropsWithoutRef, ElementType, ReactNode } from 'react'

import { cn } from '../lib/cn'

type Tone = 'default' | 'hero' | 'subtle' | 'danger'

type Props<T extends ElementType> = {
  as?: T
  children: ReactNode
  className?: string
  tone?: Tone
  padded?: boolean
} & Omit<ComponentPropsWithoutRef<T>, 'as' | 'children' | 'className'>

const TONE_CLASS: Record<Tone, string> = {
  default: 'glass-panel',
  hero: 'glass-panel glass-panel-hero',
  subtle: 'glass-panel glass-panel-subtle',
  danger: 'glass-panel glass-panel-danger',
}

export function GlassPanel<T extends ElementType = 'section'>({
  as,
  children,
  className,
  tone = 'default',
  padded = true,
  ...props
}: Props<T>) {
  const Component = as ?? 'section'
  return (
    <Component
      className={cn(TONE_CLASS[tone], padded ? 'glass-panel-padded' : '', className)}
      {...props}
    >
      {children}
    </Component>
  )
}
