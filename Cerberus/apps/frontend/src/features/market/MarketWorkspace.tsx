import { Suspense } from 'react'

import { LazyCandlesChart, PanelSkeleton } from '../../app/lazyPanels'
import { useI18n } from '../../i18n/I18nProvider'
import type { WorkspaceId, WorkspacePanelId } from '../../store/slices/shared'
import { WORKSPACE_PANELS_BY_WORKSPACE } from '../../view-models/workbench'
import {
  DiagnosticDrawer,
  FocusedWorkspacePanel,
  SectionFrame,
  SubpageLauncher,
  type SubpageLauncherItem,
  TerminalBand,
  WorkspaceOperatorDeck,
} from '../../ui'
import { useRafPresenceTransition } from '../../ui/motion/useRafPresenceTransition'
import { SymbolExecutionRail } from './components/SymbolExecutionRail'
import { useMarketWorkspaceModel } from './useMarketWorkspaceModel'

type Props = {
  active?: boolean
  onSelectWorkspace?: (workspace: WorkspaceId) => void
  panel?: WorkspacePanelId
  onSelectPanel?: (panel: WorkspacePanelId) => void
}

export function MarketWorkspace({ active = true, onSelectWorkspace, panel = 'home', onSelectPanel }: Props) {
  const { t } = useI18n()
  const model = useMarketWorkspaceModel({ active })
  const chartPhase = useRafPresenceTransition(model.activeSymbol, 320)
  const panelItems: SubpageLauncherItem[] = WORKSPACE_PANELS_BY_WORKSPACE.market
    .filter((item) => item.id !== 'home')
    .map((item) => ({
      id: item.id,
      title: t(item.titleKey),
      description: t(item.descriptionKey),
      cta: `${t(item.actionKey)} ${t(item.titleKey)}`,
    }))
  const openHome = () => onSelectPanel?.('home')
  const openPanel = (next: string) => onSelectPanel?.(next as WorkspacePanelId)
  const symbolSwitcher = (
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
  )

  const chartPanel = (
    <SectionFrame
      title={`${model.activeSymbol} ${t('market.candles')}`}
      description={t('workspace.market.chartDescription')}
      descriptionMode="srOnly"
      aside={symbolSwitcher}
      className="ws-primary-panel"
      accent="cyan"
      stage="feature"
      compactHeader
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
        <Suspense fallback={<PanelSkeleton height="280px" />}>
          <LazyCandlesChart series={model.chartSeries} markers={model.chartMarkers} height={280} />
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
  )

  if (panel === 'chart') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.market.title')}
        title={`${model.activeSymbol} ${t('market.candles')}`}
        description={t('workspace.market.chartDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
        className="fwp-market-chart"
      >
        {chartPanel}
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'quote') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.market.title')}
        title={t('workspace.market.operatorQuoteTitle')}
        description={t('workspace.market.operatorQuoteDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <SectionFrame
          title={t('workspace.market.operatorDeckTitle')}
          description={t('workspace.market.operatorDeckDescription')}
          descriptionMode="srOnly"
          aside={symbolSwitcher}
          accent="teal"
          stage="operator"
          compactHeader
          bodyClassName="operator-shell"
        >
          <WorkspaceOperatorDeck sections={model.operatorSections} layout="rail" />
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'execution-pulse') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.market.title')}
        title={t('workspace.market.executionRailTitle')}
        description={t('workspace.market.executionRailDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <SectionFrame
          title={t('workspace.market.executionRailTitle')}
          description={t('workspace.market.executionRailDescription')}
          descriptionMode="srOnly"
          aside={symbolSwitcher}
          accent="amber"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
          <SymbolExecutionRail model={model.executionRail} />
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  return (
    <div className="ws-grid ws-grid-market" data-workspace="market">
      <div className="workspace-home workspace-home-market">
        <SectionFrame
          title={t('workspace.market.title')}
          description={t('workspace.market.description')}
          descriptionMode="srOnly"
          aside={symbolSwitcher}
          className="workspace-home-main ws-primary-panel"
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
        </SectionFrame>

        <SubpageLauncher
          title={t('workspace.panel.indexTitle')}
          description={t('workspace.market.linkageTitle')}
          items={panelItems}
          onSelect={openPanel}
        />

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

        {model.summaryError ? (
          <DiagnosticDrawer title={t('workspace.market.diagnostics')} summary={model.summaryError.message}>
            <pre className="diagnostic-pre">{JSON.stringify(model.summaryError, null, 2)}</pre>
          </DiagnosticDrawer>
        ) : null}
      </div>
    </div>
  )
}
