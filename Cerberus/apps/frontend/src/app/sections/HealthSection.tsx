import { Suspense } from 'react'

import { LazyServiceHealthPanel, PanelSkeleton } from '../lazyPanels'
import type { HealthSectionProps } from './types'

export function HealthSection({ domainStatus, persistenceStatus }: HealthSectionProps) {
  return (
    <section className="mt-6">
      <div className="min-h-[180px]">
        <Suspense fallback={<PanelSkeleton height="h-[180px]" />}>
          <LazyServiceHealthPanel domainStatus={domainStatus} persistence={persistenceStatus} />
        </Suspense>
      </div>
    </section>
  )
}
