import { CandlesChart } from '../../components/CandlesChart'
import { MatchingOrderBookPanel } from '../../components/MatchingOrderBookPanel'
import { useI18n } from '../../i18n/I18nProvider'
import { DiagnosticDrawer, MetricTile, SectionFrame } from '../../ui'
import { useMarketWorkspaceModel } from './useMarketWorkspaceModel'

type Props = {
  active?: boolean
}

export function MarketWorkspace({ active = true }: Props) {
  const { t } = useI18n()
  const model = useMarketWorkspaceModel({ active })

  return (
    <div className="workspace-grid">
      <SectionFrame
        title={t('workspace.market.title')}
        description={t('workspace.market.description')}
        eyebrow={t('workspace.market.eyebrow')}
        aside={
          <div className="symbol-switcher">
            {model.symbolChips.map((chip) => (
              <button
                key={chip.id}
                type="button"
                className={chip.active ? 'chip-button chip-button-active' : 'chip-button'}
                onClick={() => model.selectSymbol(chip.id)}
                aria-pressed={chip.active}
              >
                {chip.label}
              </button>
            ))}
          </div>
        }
        className="workspace-span-full"
      >
        <div className="metric-grid">
          {model.metricTiles.map((tile) => (
            <MetricTile
              key={tile.id}
              label={tile.label}
              value={tile.value}
              tone={tile.tone}
              hint={tile.hint}
            />
          ))}
        </div>
      </SectionFrame>

      <div className="workspace-main stack">
        <SectionFrame title={`${model.activeSymbol} ${t('market.candles')}`} description={t('workspace.market.chartDescription')}>
          <div className="chart-shell">
            <CandlesChart candles={model.candles} />
          </div>
        </SectionFrame>

        {model.summaryError ? (
          <DiagnosticDrawer title={t('workspace.market.diagnostics')} summary={model.summaryError.message}>
            <pre className="diagnostic-pre">{JSON.stringify(model.summaryError, null, 2)}</pre>
          </DiagnosticDrawer>
        ) : null}
      </div>

      <div className="workspace-side">
        <MatchingOrderBookPanel orderbook={model.orderbook} />
      </div>
    </div>
  )
}
