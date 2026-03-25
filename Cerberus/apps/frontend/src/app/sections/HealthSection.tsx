import { Suspense } from 'react'

import { LazyServiceHealthPanel, PanelSkeleton } from '../lazyPanels'
import type { HealthSectionProps } from './types'

export function HealthSection({ className, domainStatus, persistenceStatus }: HealthSectionProps) {
  const sectionClassName = className ?? 'mt-6'

  return (
    <section className={sectionClassName}>
      <div className="min-h-[180px]">
        <Suspense fallback={<PanelSkeleton height="h-[180px]" />}>
          <LazyServiceHealthPanel domainStatus={domainStatus} persistence={persistenceStatus} />
        </Suspense>
      </div>
    </section>
  )
}
