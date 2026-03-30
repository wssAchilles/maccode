import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, EmptyState, GlassPanel } from '../../../ui'
import type { StrategyPortfolioPanelModel } from '../view-models'

type Props = {
  model: StrategyPortfolioPanelModel
  onSelectSymbol?: (symbol: string) => void
}

export function StrategyPortfolioPanel({ model, onSelectSymbol }: Props) {
  const { t } = useI18n()

  if (model.items.length === 0) {
    return (
      <GlassPanel className="strategy-portfolio-panel" tone="subtle">
        <EmptyState title={model.emptyTitle ?? model.summary} body={model.emptyHint ?? t('workspace.strategy.noDecisionsHint')} />
      </GlassPanel>
    )
  }

  return (
    <GlassPanel className="strategy-portfolio-panel" tone="subtle">
      <div className="strategy-panel-head">
        <div>
          <p className="subtle-label">{t('workspace.strategy.portfolioTitle')}</p>
          <p className="strategy-panel-summary">{model.summary}</p>
        </div>
        <div className="strategy-portfolio-status">
          <p className="strategy-portfolio-bias">{model.biasLabel}</p>
          <p className={model.gateTone === 'accent' ? 'strategy-portfolio-gate strategy-portfolio-gate-accent' : model.gateTone === 'muted' ? 'strategy-portfolio-gate strategy-portfolio-gate-muted' : 'strategy-portfolio-gate'}>
            {model.gateLabel}
          </p>
        </div>
      </div>

      {model.symbolChips.length > 0 ? (
        <div className="strategy-portfolio-chips" role="list" aria-label={t('workspace.strategy.coverage')}>
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

      <DataList items={model.items} />
    </GlassPanel>
  )
}
