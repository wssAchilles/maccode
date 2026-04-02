import { useI18n } from '../../../i18n/I18nProvider'
import { EmptyState, PanelSection, TerminalBand } from '../../../ui'
import type { MarketExecutionRailModel } from '../view-models'

type Props = {
  model: MarketExecutionRailModel
}

export function SymbolExecutionRail({ model }: Props) {
  const { t } = useI18n()

  return (
    <div className="market-execution-rail">
      {model.band ? <TerminalBand model={model.band} className="mer-band" /> : null}
      <PanelSection
        className="mer-section"
        eyebrow={t('workspace.market.executionRailTitle')}
        title={model.summary}
        hint={model.staleHint ?? t('workspace.market.executionRailDescription')}
      >
        {model.items.length === 0 ? (
          <EmptyState
            title={model.emptyTitle ?? model.summary}
            body={model.emptyHint ?? t('workspace.market.executionRailDescription')}
          />
        ) : (
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
        )}
      </PanelSection>
    </div>
  )
}
