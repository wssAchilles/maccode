import { Suspense } from 'react'

import { LazyCandlesChart, PanelSkeleton } from '../../app/lazyPanels'
import { useI18n } from '../../i18n/I18nProvider'
import type { WorkspaceId } from '../../store/slices/shared'
import {
  DiagnosticDrawer,
  GlassPanel,
  MetricTile,
  SectionFrame,
  TerminalBand,
  WorkspaceOperatorDeck,
  WorkspaceSpotlight,
} from '../../ui'
import { useRafPresenceTransition } from '../../ui/motion/useRafPresenceTransition'
import { SymbolExecutionRail } from './components/SymbolExecutionRail'
import { useMarketWorkspaceModel } from './useMarketWorkspaceModel'

type Props = {
  active?: boolean
  onSelectWorkspace?: (workspace: WorkspaceId) => void
}

export function MarketWorkspace({ active = true, onSelectWorkspace }: Props) {
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
        <div className="ws-hero-grid">
          <WorkspaceSpotlight model={model.spotlight} className="ws-hero-spotlight" />
          <div className="ws-hero-side hero-side-shell">
            <div className="hero-side-head">
              <p className="subtle-label">{t('workspace.hero.readings')}</p>
            </div>
            <div className="metric-grid ws-hero-metrics">
              {model.metricTiles.map((tile, index) => (
                <MetricTile
                  key={tile.id}
                  label={tile.label}
                  value={tile.value}
                  tone={tile.tone}
                  hint={tile.hint}
                  className={index === 0 ? 'hero-metric hero-metric-primary' : 'hero-metric'}
                />
              ))}
            </div>
          </div>
        </div>
      </SectionFrame>

      <div className="ws-main stack wsm">
        <SectionFrame
          title={t('workspace.market.operatorDeckTitle')}
          description={t('workspace.market.operatorDeckDescription')}
          accent="teal"
          stage="operator"
          compactHeader
          bodyClassName="operator-shell"
        >
          <WorkspaceOperatorDeck sections={model.operatorSections} layout="rail" />
        </SectionFrame>

        <SectionFrame
          title={`${model.activeSymbol} ${t('market.candles')}`}
          description={t('workspace.market.chartDescription')}
          accent="cyan"
          stage="feature"
        >
          <TerminalBand model={model.chartBand} className="cc-band" compact hideHint hideEyebrow />
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
                    <p
                      className={
                        metric.tone === 'negative'
                          ? 'cc-value dl-value-negative'
                          : metric.tone === 'positive'
                            ? 'cc-value dl-value-positive'
                            : metric.tone === 'accent'
                              ? 'cc-value dl-value-accent'
                              : 'cc-value'
                      }
                    >
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

        <SectionFrame title={t('workspace.nav')} description={t('workspace.market.linkageTitle')} accent="amber" stage="tail">
          <div className="ws-actions">
            <button type="button" className="soft-button sbp" onClick={() => onSelectWorkspace?.('book')}>
              {t('workspace.cta.book')}
            </button>
            <button type="button" className="soft-button" onClick={() => onSelectWorkspace?.('execution')}>
              {t('workspace.cta.execution')}
            </button>
            <button type="button" className="soft-button" onClick={() => onSelectWorkspace?.('strategy')}>
              {t('workspace.cta.strategy')}
            </button>
          </div>
        </SectionFrame>

        {model.summaryError ? (
          <DiagnosticDrawer title={t('workspace.market.diagnostics')} summary={model.summaryError.message}>
            <pre className="diagnostic-pre">{JSON.stringify(model.summaryError, null, 2)}</pre>
          </DiagnosticDrawer>
        ) : null}
      </div>

      <div className="ws-side stack wss">
        <GlassPanel className="rail-shell" tone="subtle">
          <TerminalBand model={model.inspectorBand} className="inspector-band" compact hideHint hideEyebrow />
        </GlassPanel>
        <SectionFrame
          title={t('workspace.market.executionRailTitle')}
          description={t('workspace.market.executionRailDescription')}
          accent="amber"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
          <SymbolExecutionRail model={model.executionRail} />
        </SectionFrame>
      </div>
    </div>
  )
}
