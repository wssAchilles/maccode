import { CandlesChart } from '../../components/CandlesChart'
import { ExecutionTimelinePanel } from '../../components/ExecutionTimelinePanel'
import { MatchingOrderBookPanel } from '../../components/MatchingOrderBookPanel'
import { useI18n } from '../../i18n/I18nProvider'
import { DiagnosticDrawer, MetricTile, SectionFrame } from '../../ui'
import { StrategyDecisionMatrix } from '../strategy-orchestration/components/StrategyDecisionMatrix'
import { StrategyPortfolioPanel } from '../strategy-orchestration/components/StrategyPortfolioPanel'
import { StrategyRegistryPanel } from '../strategy-orchestration/components/StrategyRegistryPanel'
import { SymbolExecutionRail } from './components/SymbolExecutionRail'
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
          <div
            className="chart-shell"
            aria-busy={model.chartState.state === 'loading'}
            data-state={model.chartState.state}
          >
            <CandlesChart candles={model.candles} markers={model.chartMarkers} />
            {model.chartState.state !== 'ready' ? (
              <div
                className={`chart-overlay chart-overlay-${model.chartState.state}`}
                role={model.chartState.state === 'loading' ? 'status' : 'note'}
                aria-live="polite"
              >
                <p className="chart-overlay-title">{model.chartState.title}</p>
                <p className="chart-overlay-hint">{model.chartState.hint}</p>
              </div>
            ) : null}
          </div>
        </SectionFrame>

        <SectionFrame
          title={t('workspace.market.executionRailTitle')}
          description={t('workspace.market.executionRailDescription')}
        >
          <SymbolExecutionRail model={model.executionRail} />
        </SectionFrame>

        {model.summaryError ? (
          <DiagnosticDrawer title={t('workspace.market.diagnostics')} summary={model.summaryError.message}>
            <pre className="diagnostic-pre">{JSON.stringify(model.summaryError, null, 2)}</pre>
          </DiagnosticDrawer>
        ) : null}

        <SectionFrame
          title={t('workspace.strategy.title')}
          description={t('workspace.strategy.description')}
        >
          <StrategyDecisionMatrix model={model.strategyMatrix} />
        </SectionFrame>

        <SectionFrame
          title={t('execution.timeline')}
          description={t('workspace.market.executionRailDescription')}
          className="timeline-section"
        >
          <ExecutionTimelinePanel active={active} />
        </SectionFrame>
      </div>

      <div className="workspace-side stack">
        <SectionFrame
          title={t('workspace.strategy.portfolioTitle')}
          description={t('workspace.strategy.portfolioDescription')}
        >
          <StrategyPortfolioPanel model={model.portfolioPanel} onSelectSymbol={model.selectSymbol} />
        </SectionFrame>
        <SectionFrame
          title={t('workspace.strategy.registryTitle')}
          description={t('workspace.strategy.registryDescription')}
        >
          <StrategyRegistryPanel model={model.strategyRegistry} />
        </SectionFrame>
        <MatchingOrderBookPanel orderbook={model.orderbook} />
      </div>
    </div>
  )
}
