import type { ServiceHealthPanelModel } from '../features/health/view-models'
import { DataList, GlassPanel, StatusPill } from '../ui'

type Props = {
  model: ServiceHealthPanelModel
}

export function ServiceHealthPanel({ model }: Props) {
  return (
    <div className="stack" data-testid="service-health-panel">
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

      {model.persistenceGroups.length > 0 ? (
        <div className="health-grid">
          {model.persistenceGroups.map((items) => (
            <GlassPanel key={items[0]?.id ?? 'group'} tone="subtle">
              <DataList items={items} />
            </GlassPanel>
          ))}
        </div>
      ) : null}
    </div>
  )
}
