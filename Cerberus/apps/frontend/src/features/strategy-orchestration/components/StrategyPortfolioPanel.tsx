import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, EmptyState, PanelSection, TerminalBand } from '../../../ui'
import type { StrategyPortfolioPanelModel } from '../view-models'

type Props = {
  model: StrategyPortfolioPanelModel
  onSelectSymbol?: (symbol: string) => void
}

export function StrategyPortfolioPanel({ model, onSelectSymbol }: Props) {
  const { t } = useI18n()

  return (
    <div className="sp">
      <TerminalBand model={model.band} className="sp-band" compact />
      <PanelSection
        className="spf-section"
        eyebrow={t('workspace.strategy.portfolioTitle')}
        title={model.summary}
        hint={t('workspace.strategy.portfolioDescription')}
        aside={
          <div className="spf-status">
            <p className="spf-bias">{model.biasLabel}</p>
            <p
              className={
                model.gateTone === 'accent'
                  ? 'spf-gate spf-gate-accent'
                  : model.gateTone === 'muted'
                    ? 'spf-gate spf-gate-muted'
                    : 'spf-gate'
              }
            >
              {model.gateLabel}
            </p>
          </div>
        }
      >
        {model.symbolChips.length > 0 ? (
          <div className="spf-chips" role="list" aria-label={t('workspace.strategy.coverage')}>
            {model.symbolChips.map((chip) => (
              <div key={chip.id} role="listitem">
                <button
                  type="button"
                  className={chip.active ? 'chip-button chip-button-active' : 'chip-button'}
                  onClick={() => onSelectSymbol?.(chip.id)}
                  aria-pressed={chip.active}
                >
                  {chip.label}
                </button>
              </div>
            ))}
          </div>
        ) : null}

        {model.items.length === 0 ? (
          <EmptyState title={model.emptyTitle ?? model.summary} body={model.emptyHint ?? t('workspace.strategy.noDecisionsHint')} />
        ) : (
          <DataList items={model.items} />
        )}
      </PanelSection>
    </div>
  )
}
