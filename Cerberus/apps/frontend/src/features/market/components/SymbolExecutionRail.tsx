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
      <div className="sp-head">
        <div>
          <p className="subtle-label">{t('workspace.market.executionRailTitle')}</p>
          <p className="sp-summary">{model.summary}</p>
          {model.staleHint ? <p className="sp-hint">{model.staleHint}</p> : null}
        </div>
      </div>
      <div className="mer-list" role="list" aria-label={t('workspace.market.executionRailTitle')}>
        {model.items.map((item) => (
          <article key={item.id} role="listitem" className="mer-row">
            <div className="mer-main">
              <p className="tr-title">{item.title}</p>
              <p className="tr-subtitle">{item.subtitle}</p>
            </div>
            <div className="mer-side">
              <p className="tr-status">{item.status}</p>
              <p className="tr-time">{item.time}</p>
            </div>
          </article>
        ))}
      </div>
    </GlassPanel>
  )
}
