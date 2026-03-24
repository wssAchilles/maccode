import type { DomainName, DomainStatusMap } from '../store/slices/shared'
import type { PersistenceStatus } from '../types/contracts'
import { useI18n } from '../i18n/I18nProvider'

type Props = {
  domainStatus: DomainStatusMap
  persistence?: PersistenceStatus
}

function stateClass(state: string): string {
  if (state === 'ready') {
    return 'status-chip status-ready'
  }
  if (state === 'degraded') {
    return 'status-chip status-degraded'
  }
  if (state === 'error') {
    return 'status-chip status-error'
  }
  if (state === 'loading') {
    return 'status-chip status-loading'
  }
  return 'status-chip'
}

function domainLabel(domain: DomainName, t: ReturnType<typeof useI18n>['t']): string {
  if (domain === 'market-stream') {
    return t('health.domain.market')
  }
  if (domain === 'strategy-summary') {
    return t('health.domain.strategy')
  }
  return t('health.domain.execution')
}

function stateLabel(state: string, t: ReturnType<typeof useI18n>['t']): string {
  if (state === 'idle') {
    return t('health.state.idle')
  }
  if (state === 'loading') {
    return t('health.state.loading')
  }
  if (state === 'ready') {
    return t('health.state.ready')
  }
  if (state === 'degraded') {
    return t('health.state.degraded')
  }
  if (state === 'error') {
    return t('health.state.error')
  }
  return state
}

export function ServiceHealthPanel({ domainStatus, persistence }: Props) {
  const { t } = useI18n()

  return (
    <section className="panel-card">
      <h2 className="panel-title">{t('section.health')}</h2>

      <div className="mt-3 grid gap-3 md:grid-cols-3">
        {(Object.keys(domainStatus) as DomainName[]).map((domain) => {
          const item = domainStatus[domain]
          return (
            <article key={domain} className="rounded-xl border border-slate-700/60 bg-slate-950/40 p-3">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm text-slate-200">{domainLabel(domain, t)}</h3>
                <span className={stateClass(item.state)}>{stateLabel(item.state, t)}</span>
              </div>
              <p className="mt-2 text-xs text-slate-400">
                {item.stale ? t('health.stale') : t('health.fresh')}
              </p>
              <p className="mt-1 text-[11px] text-slate-500">
                {t('common.updatedAt')}:{' '}
                {item.last_update_ms ? new Date(item.last_update_ms).toLocaleTimeString() : t('common.na')}
              </p>
              {item.reason ? <p className="mt-1 text-[11px] text-amber-200">{item.reason}</p> : null}
            </article>
          )
        })}
      </div>

      {persistence ? (
        <div className="mt-4 grid gap-3 rounded-xl border border-slate-700/60 bg-slate-950/45 p-3 text-xs md:grid-cols-2">
          <div>
            <p className="text-slate-400">{t('strategy.persistence')}</p>
            <p className="mt-1 text-slate-200">
              status: {persistence.status} | ticks: {persistence.worker.processed_ticks}
            </p>
            <p className="mt-1 text-slate-500">
              supabase:{' '}
              {persistence.stores.supabase_enabled ? t('common.ready') : t('common.disabled')} | firestore:{' '}
              {persistence.stores.firebase_enabled ? t('common.ready') : t('common.disabled')}
            </p>
          </div>
          <div>
            <p className="text-slate-400">{t('strategy.matching')}</p>
            <p className="mt-1 text-slate-200">
              {persistence.matching?.health?.status ?? t('common.disabled')} | trades:{' '}
              {persistence.matching?.stats?.trade_count ?? 0}
            </p>
            <p className="mt-1 text-slate-500">
              live orders: {persistence.matching?.stats?.live_orders ?? 0} | symbols:{' '}
              {persistence.matching?.stats?.symbols ?? 0}
            </p>
          </div>
        </div>
      ) : null}
    </section>
  )
}
