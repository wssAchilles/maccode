import { Suspense } from 'react'

import {
  LazyExecutionStrategyOperationsDrawerContent,
  LazyExecutionConsole,
  LazyExecutionTimelinePanel,
  LazyMatchingOrderBookPanel,
  PanelSkeleton,
} from '../../app/lazyPanels'
import { useI18n } from '../../i18n/I18nProvider'
import { DiagnosticDrawer, GlassPanel, MetricTile, SectionFrame, TerminalBand, WorkspaceOperatorDeck, WorkspaceSpotlight } from '../../ui'
import { ExecutionOperationsPanel } from './components/ExecutionOperationsPanel'
import { ExecutionLifecyclePanel } from '../strategy-orchestration/components/ExecutionLifecyclePanel'
import { StrategyOrchestrationAuditTimeline } from '../strategy-orchestration/components/StrategyOrchestrationAuditTimeline'
import { StrategyDecisionMatrix } from '../strategy-orchestration/components/StrategyDecisionMatrix'
import { StrategyPortfolioPanel } from '../strategy-orchestration/components/StrategyPortfolioPanel'
import { StrategyRegistryPanel } from '../strategy-orchestration/components/StrategyRegistryPanel'
import { useExecutionWorkspaceModel } from './useExecutionWorkspaceModel'

type Props = {
  active?: boolean
}

export function ExecutionWorkspace({ active = true }: Props) {
  const { t } = useI18n()
  const model = useExecutionWorkspaceModel({ active })

  return (
    <div className="ws-grid ws-grid-execution" data-workspace="execution">
      <SectionFrame
        title={t('workspace.execution.title')}
        description={t('workspace.execution.description')}
        eyebrow={t('workspace.execution.eyebrow')}
        className="ws-span-full"
        tone="hero"
        accent="amber"
        stage="hero"
      >
        <TerminalBand model={model.heroBand} className="hero-band" />
        <div className="ws-hero-grid">
          <WorkspaceSpotlight model={model.spotlight} className="ws-hero-spotlight" />
          <div className="ws-hero-side">
            <div className="metric-grid ws-hero-metrics">
              {model.metricTiles.map((tile) => (
                <MetricTile
                  key={tile.id}
                  label={tile.label}
                  value={tile.value}
                  hint={tile.hint}
                  tone={tile.tone}
                />
              ))}
            </div>
          </div>
        </div>
      </SectionFrame>

      <div className="ws-main stack wsm">
        <SectionFrame
          title={t('workspace.execution.operatorDeckTitle')}
          description={t('workspace.execution.operatorDeckDescription')}
          accent="teal"
          stage="operator"
          compactHeader
          bodyClassName="operator-shell"
        >
          <WorkspaceOperatorDeck sections={model.operatorSections} layout="rail" />
        </SectionFrame>

        <SectionFrame
          title={t('workspace.execution.lifecycleTitle')}
          description={t('workspace.execution.lifecycleDescription')}
          accent="cyan"
          stage="feature"
        >
          <ExecutionLifecyclePanel model={model.lifecyclePanel} />
        </SectionFrame>
      </div>

      <div className="ws-side stack xsd wss">
        <GlassPanel className="rail-shell" tone="subtle">
          <TerminalBand model={model.inspectorBand} className="inspector-band" compact hideHint hideEyebrow />
        </GlassPanel>
        <SectionFrame
          title={t('workspace.strategy.matrixTitle')}
          description={t('workspace.strategy.description')}
          bodyClassName="inspector-shell"
          accent="teal"
          stage="inspector"
          compactHeader
        >
          <div className="stack">
            <TerminalBand model={model.strategyBand} className="strategy-band" compact hideHint hideEyebrow />
            <StrategyPortfolioPanel model={model.portfolioPanel} onSelectSymbol={model.selectSymbol} />
            <StrategyDecisionMatrix model={model.strategyMatrix} />
            <DiagnosticDrawer
              title={t('workspace.strategy.registryTitle')}
              summary={t('workspace.strategy.registryDescription')}
              contentClassName="tail-drawer"
            >
              <StrategyRegistryPanel model={model.strategyRegistry} />
            </DiagnosticDrawer>
            <DiagnosticDrawer
              title={t('workspace.strategy.auditTimelineTitle')}
              summary={t('workspace.strategy.auditTimelineHint')}
              contentClassName="tail-drawer"
            >
              <StrategyOrchestrationAuditTimeline model={model.strategyAuditTimeline} />
            </DiagnosticDrawer>
          </div>
        </SectionFrame>

        <Suspense fallback={<PanelSkeleton height="300px" />}>
          <LazyMatchingOrderBookPanel model={model.orderbookPanel} />
        </Suspense>

        {model.summaryError ? (
          <DiagnosticDrawer title={t('workspace.execution.diagnostics')} summary={model.summaryError.message}>
            <pre className="diagnostic-pre">{JSON.stringify(model.summaryError, null, 2)}</pre>
          </DiagnosticDrawer>
        ) : null}
        <SectionFrame
          title={t('execution.timeline')}
          description={t('workspace.execution.timelineDescription')}
          className="xts"
          accent="cyan"
          stage="tail"
          compactHeader
          bodyClassName="tail-shell"
        >
          <Suspense fallback={<PanelSkeleton height="320px" />}>
            <LazyExecutionTimelinePanel active={active} />
          </Suspense>
        </SectionFrame>
      </div>

      <SectionFrame
        title={t('workspace.execution.operationsTitle')}
        description={t('workspace.execution.operationsDescription')}
        className="ws-span-full"
        accent="amber"
        stage="operator"
      >
        <ExecutionOperationsPanel model={model.operationsPanel} />
      </SectionFrame>

      <SectionFrame
        title={t('workspace.strategy.operationsTitle')}
        description={t('workspace.strategy.operationsDescription')}
        className="ws-span-full"
        accent="teal"
        stage="tail"
        compactHeader
        bodyClassName="tail-shell"
      >
        <DiagnosticDrawer
          title={t('workspace.strategy.operationsTitle')}
          summary={t('workspace.strategy.operationsDescription')}
          testId="execution-strategy-operations-drawer"
          contentClassName="tail-drawer"
        >
          <Suspense fallback={<PanelSkeleton height="420px" />}>
            <LazyExecutionStrategyOperationsDrawerContent active={active} />
          </Suspense>
        </DiagnosticDrawer>
      </SectionFrame>

      <SectionFrame
        title={t('workspace.execution.ticketTitle')}
        description={t('workspace.execution.ticketDescription')}
        className="ws-span-full"
        accent="amber"
        stage="tail"
        compactHeader
        bodyClassName="tail-shell"
      >
        <Suspense fallback={<PanelSkeleton height="540px" />}>
          <LazyExecutionConsole
            active={active}
            selectedSymbol={model.selectedSymbol}
            latestBid={model.displayQuote?.bid_price}
            latestAsk={model.displayQuote?.ask_price}
          />
        </Suspense>
      </SectionFrame>
    </div>
  )
}
