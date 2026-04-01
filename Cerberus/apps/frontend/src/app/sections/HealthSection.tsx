import { Suspense } from 'react'

import { useI18n } from '../../i18n/I18nProvider'
import { buildServiceHealthPanelModel } from '../../features/health/view-models'
import { LazyServiceHealthPanel, PanelSkeleton } from '../lazyPanels'
import type { HealthSectionProps } from './types'

export function HealthSection({ className, domainStatus, persistenceStatus }: HealthSectionProps) {
  const { t } = useI18n()
  const sectionClassName = className ?? 'mt-6'
  const panelModel = buildServiceHealthPanelModel({
    t,
    domainStatus,
    persistenceStatus,
  })

  return (
    <section className={sectionClassName} aria-label={t('workspace.health.title')}>
      <div className="min-h-[180px]">
        <Suspense fallback={<PanelSkeleton height="h-[180px]" />}>
          <LazyServiceHealthPanel model={panelModel} />
        </Suspense>
      </div>
    </section>
  )
}
