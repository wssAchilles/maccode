import type { ServiceHealthPanelModel } from '../features/health/view-models'
import { useI18n } from '../i18n/I18nProvider'
import { DataList, GlassPanel, StatusPill, TerminalBand } from '../ui'

type Props = {
  model: ServiceHealthPanelModel
}

export function ServiceHealthPanel({ model }: Props) {
  const { t } = useI18n()

  return (
    <div className="stack" data-testid="service-health-panel">
      <TerminalBand model={model.band} className="hp-band" />
      <section className="hp-section">
        <div className="ids-group">
          <p className="subtle-label">{t('workspace.health.title')}</p>
          <p className="sp-hint">{model.updatedAtLabel}</p>
        </div>
        <div className="health-grid">
          {model.cards.map((card) => (
            <GlassPanel key={card.id} className="health-card" tone="subtle">
              <div className="hc-head">
                <div>
                  <p className="hc-title">{card.title}</p>
                  <p className="hc-meta">{card.staleLabel}</p>
                </div>
                <StatusPill state={card.state} label={card.stateLabel} compact />
              </div>
              <p className="hc-updated">{model.updatedAtLabel}: {card.updatedAt}</p>
              {card.requestId ? <p className="hc-request">{model.requestIdLabel}: {card.requestId}</p> : null}
              {card.reason ? <p className="hc-reason">{card.reason}</p> : null}
            </GlassPanel>
          ))}
        </div>
      </section>

      {model.persistenceGroups.length > 0 ? (
        <section className="hp-section">
          <div className="ids-group">
            <p className="subtle-label">{t('workspace.health.persistenceTitle')}</p>
            <p className="sp-hint">{model.band.hint}</p>
          </div>
          <div className="health-grid">
            {model.persistenceGroups.map((items) => (
              <GlassPanel key={items[0]?.id ?? 'group'} tone="subtle" className="hp-persistence-card">
                <DataList items={items} />
              </GlassPanel>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}
