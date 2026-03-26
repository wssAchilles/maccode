import { ServiceHealthPanel } from '../../components/ServiceHealthPanel'
import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import { DataList, DiagnosticDrawer, GlassPanel, SectionFrame } from '../../ui'

type Props = {
  active?: boolean
}

export function HealthWorkspace({ active: _active = true }: Props) {
  const { t } = useI18n()
  const domainStatus = useCerberusStore((state) => state.uiState.domain_status)
  const persistenceStatus = useCerberusStore((state) => state.strategySummary.persistence_status)
  const summaryError = useCerberusStore((state) => state.strategySummary.last_error)

  return (
    <div className="workspace-grid">
      <SectionFrame
        title={t('workspace.health.title')}
        description={t('workspace.health.description')}
        eyebrow={t('workspace.health.eyebrow')}
        className="workspace-span-full"
      >
        <ServiceHealthPanel domainStatus={domainStatus} persistence={persistenceStatus} />
      </SectionFrame>

      <div className="workspace-main stack">
        <SectionFrame title={t('workspace.health.persistenceTitle')} description={t('workspace.health.persistenceDescription')}>
          <div className="health-grid">
            <GlassPanel tone="subtle">
              <DataList
                items={[
                  {
                    id: 'processed',
                    label: t('strategy.ticksProcessed'),
                    value: String(persistenceStatus?.worker.processed_ticks ?? 0),
                  },
                  {
                    id: 'trackedSymbols',
                    label: t('workspace.health.trackedSymbols'),
                    value: String(persistenceStatus?.worker.tracked_symbols?.length ?? 0),
                  },
                  {
                    id: 'started',
                    label: t('workspace.health.workerStarted'),
                    value: String(persistenceStatus?.worker.started ?? false),
                  },
                ]}
              />
            </GlassPanel>
            <GlassPanel tone="subtle">
              <DataList
                items={[
                  {
                    id: 'supabase',
                    label: 'Supabase',
                    value: String(persistenceStatus?.stores.supabase_enabled ?? false),
                  },
                  {
                    id: 'firebase',
                    label: 'Firestore',
                    value: String(persistenceStatus?.stores.firebase_enabled ?? false),
                  },
                  {
                    id: 'matching',
                    label: t('strategy.matching'),
                    value: persistenceStatus?.matching?.health?.status ?? t('common.disabled'),
                  },
                ]}
              />
            </GlassPanel>
          </div>
        </SectionFrame>
      </div>

      <div className="workspace-side stack">
        <DiagnosticDrawer
          title={t('workspace.health.requestIds')}
          summary={t('workspace.health.requestIdsDescription')}
          defaultOpen={Boolean(summaryError)}
        >
          <pre className="diagnostic-pre">
            {JSON.stringify(
              {
                summaryError,
                domainStatus,
              },
              null,
              2,
            )}
          </pre>
        </DiagnosticDrawer>
      </div>
    </div>
  )
}
