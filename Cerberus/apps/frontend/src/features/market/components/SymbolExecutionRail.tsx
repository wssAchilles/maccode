import { useI18n } from '../../../i18n/I18nProvider'
import { EmptyState, GlassPanel } from '../../../ui'
import type { MarketExecutionRailModel } from '../view-models'

type Props = {
  model: MarketExecutionRailModel
}

export function SymbolExecutionRail({ model }: Props) {
  const { t } = useI18n()

  if (model.items.length === 0) {
    return (
      <GlassPanel className="market-execution-rail" tone="subtle">
        <EmptyState
          title={model.emptyTitle ?? model.summary}
          body={model.emptyHint ?? t('workspace.market.executionRailDescription')}
        />
      </GlassPanel>
    )
  }

  return (
    <GlassPanel className="market-execution-rail" tone="subtle">
      <div className="strategy-panel-head">
        <div>
          <p className="subtle-label">{t('workspace.market.executionRailTitle')}</p>
          <p className="strategy-panel-summary">{model.summary}</p>
          {model.staleHint ? <p className="strategy-panel-hint">{model.staleHint}</p> : null}
        </div>
      </div>
      <div className="market-execution-rail-list" role="list" aria-label={t('workspace.market.executionRailTitle')}>
        {model.items.map((item) => (
          <article key={item.id} role="listitem" className="market-execution-rail-row">
            <div className="market-execution-rail-main">
              <p className="timeline-row-title">{item.title}</p>
              <p className="timeline-row-subtitle">{item.subtitle}</p>
            </div>
            <div className="market-execution-rail-side">
              <p className="timeline-row-status">{item.status}</p>
              <p className="timeline-row-time">{item.time}</p>
            </div>
          </article>
        ))}
      </div>
    </GlassPanel>
  )
}
