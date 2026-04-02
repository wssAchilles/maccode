import { Suspense } from 'react'

import {
  LazyCandlesChart,
  LazyExecutionTimelinePanel,
  LazyMatchingOrderBookPanel,
  PanelSkeleton,
} from '../../app/lazyPanels'
import { useI18n } from '../../i18n/I18nProvider'
import { DiagnosticDrawer, GlassPanel, MetricTile, SectionFrame, TerminalBand, WorkspaceOperatorDeck, WorkspaceSpotlight } from '../../ui'
import { useRafPresenceTransition } from '../../ui/motion/useRafPresenceTransition'
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
  const chartPhase = useRafPresenceTransition(model.activeSymbol, 320)

  return (
    <div className="ws-grid ws-grid-market" data-workspace="market">
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
        className="ws-span-full"
        tone="hero"
        accent="cyan"
        stage="hero"
      >
        <TerminalBand model={model.heroBand} className="hero-band" />
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

      <div className="ws-main stack wsm">
        <SectionFrame
          title={t('workspace.market.linkageTitle')}
          description={t('workspace.market.linkageHint').replace('{symbol}', model.activeSymbol)}
          accent="cyan"
          stage="feature"
        >
          <WorkspaceSpotlight model={model.spotlight} />
        </SectionFrame>

        <SectionFrame
          title={t('workspace.market.operatorDeckTitle')}
          description={t('workspace.market.operatorDeckDescription')}
          accent="teal"
          stage="operator"
        >
          <WorkspaceOperatorDeck sections={model.operatorSections} layout="rail" />
        </SectionFrame>

        <SectionFrame
          title={`${model.activeSymbol} ${t('market.candles')}`}
          description={t('workspace.market.chartDescription')}
          accent="cyan"
          stage="feature"
        >
          <TerminalBand model={model.chartBand} className="cc-band" compact />
          <div className="cc" data-phase={chartPhase}>
            <div className="cc-copy">
              <p className="subtle-label">{model.chartContext.eyebrow}</p>
              <p className="cc-summary">{model.chartContext.summary}</p>
              <p className="panel-caption">{model.chartContext.hint}</p>
            </div>
            <div className="cc-side">
              <div className="cc-chips">
                {model.chartContext.chips.map((chip, index) => (
                  <span key={`${chip}-${index}`} className="account-pill">
                    {chip}
                  </span>
                ))}
              </div>
              <div className="cc-metrics">
                {model.chartContext.metrics.map((metric) => (
                  <div key={metric.id} className="cc-metric">
                    <p className="subtle-label">{metric.label}</p>
                    <p className={metric.tone === 'negative' ? 'cc-value dl-value-negative' : metric.tone === 'positive' ? 'cc-value dl-value-positive' : metric.tone === 'accent' ? 'cc-value dl-value-accent' : 'cc-value'}>
                      {metric.value}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div
            className="chart-shell"
            aria-busy={model.chartState.state === 'loading'}
            data-state={model.chartState.state}
            data-phase={chartPhase}
          >
            <Suspense fallback={<PanelSkeleton height="340px" />}>
              <LazyCandlesChart series={model.chartSeries} markers={model.chartMarkers} />
            </Suspense>
            {model.chartState.state !== 'ready' ? (
              <div
                className={`co co-${model.chartState.state}`}
                role={model.chartState.state === 'loading' ? 'status' : 'note'}
                aria-live="polite"
              >
                <p className="co-title">{model.chartState.title}</p>
                <p className="co-hint">{model.chartState.hint}</p>
              </div>
            ) : null}
          </div>
        </SectionFrame>

        <SectionFrame
          title={t('workspace.market.executionRailTitle')}
          description={t('workspace.market.executionRailDescription')}
          accent="amber"
          stage="operator"
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
          accent="teal"
          stage="feature"
        >
          <TerminalBand model={model.strategyBand} className="strategy-band" compact />
          <StrategyDecisionMatrix model={model.strategyMatrix} />
        </SectionFrame>

        <SectionFrame
          title={t('execution.timeline')}
          description={t('workspace.market.executionRailDescription')}
          className="xts"
          accent="amber"
          stage="tail"
          bodyClassName="tail-shell"
        >
          {model.executionRail.band ? <TerminalBand model={model.executionRail.band} className="tail-band" compact /> : null}
          <Suspense fallback={<PanelSkeleton height="320px" />}>
            <LazyExecutionTimelinePanel active={active} />
          </Suspense>
        </SectionFrame>
      </div>

      <div className="ws-side stack wss">
        <GlassPanel className="rail-shell" tone="subtle">
          <TerminalBand model={model.inspectorBand} className="inspector-band" compact />
        </GlassPanel>
        <SectionFrame
          title={t('workspace.strategy.portfolioTitle')}
          description={t('workspace.strategy.portfolioDescription')}
          accent="teal"
          stage="inspector"
          bodyClassName="inspector-shell"
        >
          <StrategyPortfolioPanel model={model.portfolioPanel} onSelectSymbol={model.selectSymbol} />
        </SectionFrame>
        <SectionFrame
          title={t('workspace.strategy.registryTitle')}
          description={t('workspace.strategy.registryDescription')}
          accent="cyan"
          stage="inspector"
          bodyClassName="inspector-shell"
        >
          <StrategyRegistryPanel model={model.strategyRegistry} />
        </SectionFrame>
        <Suspense fallback={<PanelSkeleton height="300px" />}>
          <LazyMatchingOrderBookPanel model={model.orderbookPanel} />
        </Suspense>
      </div>
    </div>
  )
}
