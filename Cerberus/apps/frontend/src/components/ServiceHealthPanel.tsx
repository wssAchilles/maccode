import type { DomainStatusMap } from '../store/slices/shared'
import type { PersistenceStatus } from '../types/contracts'
import { useI18n } from '../i18n/I18nProvider'
import { buildHealthCards } from '../view-models/workbench'
import { DataList, GlassPanel, StatusPill } from '../ui'

type Props = {
  domainStatus: DomainStatusMap
  persistence?: PersistenceStatus
}

export function ServiceHealthPanel({ domainStatus, persistence }: Props) {
  const { t } = useI18n()
  const cards = buildHealthCards(domainStatus, t)

  return (
    <div className="stack" data-testid="service-health-panel">
      <div className="health-grid">
        {cards.map((card) => (
          <GlassPanel key={card.id} className="health-card" tone="subtle">
            <div className="health-card-head">
              <div>
                <p className="health-card-title">{card.title}</p>
                <p className="health-card-meta">{card.staleLabel}</p>
              </div>
              <StatusPill state={card.state} label={card.stateLabel} compact />
            </div>
            <p className="health-card-updated">{t('common.updatedAt')}: {card.updatedAt}</p>
            {card.requestId ? <p className="health-card-request">{t('health.requestId')}: {card.requestId}</p> : null}
            {card.reason ? <p className="health-card-reason">{card.reason}</p> : null}
          </GlassPanel>
        ))}
      </div>

      {persistence ? (
        <div className="health-grid">
          <GlassPanel tone="subtle">
            <DataList
              items={[
                { id: 'status', label: t('strategy.persistence'), value: persistence.status },
                { id: 'ticks', label: t('strategy.ticksProcessed'), value: String(persistence.worker.processed_ticks) },
                { id: 'supabase', label: 'Supabase', value: persistence.stores.supabase_enabled ? t('common.ready') : t('common.disabled') },
                { id: 'firebase', label: 'Firestore', value: persistence.stores.firebase_enabled ? t('common.ready') : t('common.disabled') },
              ]}
            />
          </GlassPanel>
          <GlassPanel tone="subtle">
            <DataList
              items={[
                { id: 'matchingStatus', label: t('strategy.matching'), value: persistence.matching?.health?.status ?? t('common.disabled') },
                { id: 'liveOrders', label: 'Live orders', value: String(persistence.matching?.stats?.live_orders ?? 0) },
                { id: 'trades', label: 'Trades', value: String(persistence.matching?.stats?.trade_count ?? 0) },
                { id: 'symbols', label: 'Symbols', value: String(persistence.matching?.stats?.symbols ?? 0) },
              ]}
            />
          </GlassPanel>
        </div>
      ) : null}
    </div>
  )
}
