import { ExecutionConsole } from '../../components/ExecutionConsole'
import { ExecutionTimelinePanel } from '../../components/ExecutionTimelinePanel'
import { MatchingOrderBookPanel } from '../../components/MatchingOrderBookPanel'
import { useI18n } from '../../i18n/I18nProvider'
import { DiagnosticDrawer, MetricTile, SectionFrame } from '../../ui'
import { ExecutionOperationsPanel } from './components/ExecutionOperationsPanel'
import { ExecutionLifecyclePanel } from '../strategy-orchestration/components/ExecutionLifecyclePanel'
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
    <div className="workspace-grid">
      <SectionFrame
        title={t('workspace.execution.title')}
        description={t('workspace.execution.description')}
        eyebrow={t('workspace.execution.eyebrow')}
        className="workspace-span-full"
      >
        <div className="metric-grid">
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
      </SectionFrame>

      <div className="workspace-main stack">
        <SectionFrame
          title={t('workspace.execution.lifecycleTitle')}
          description={t('workspace.execution.lifecycleDescription')}
        >
          <ExecutionLifecyclePanel model={model.lifecyclePanel} />
        </SectionFrame>

        <SectionFrame
          title={t('workspace.execution.operationsTitle')}
          description={t('workspace.execution.operationsDescription')}
        >
          <ExecutionOperationsPanel model={model.operationsPanel} />
        </SectionFrame>

        <SectionFrame title={t('workspace.execution.ticketTitle')} description={t('workspace.execution.ticketDescription')}>
          <ExecutionConsole
            active={active}
            selectedSymbol={model.selectedSymbol}
            latestBid={model.displayQuote?.bid_price}
            latestAsk={model.displayQuote?.ask_price}
          />
        </SectionFrame>
      </div>

      <div className="workspace-side stack execution-side">
        <SectionFrame
          title={t('workspace.strategy.matrixTitle')}
          description={t('workspace.strategy.description')}
        >
          <div className="stack">
            <StrategyPortfolioPanel model={model.portfolioPanel} onSelectSymbol={model.selectSymbol} />
            <StrategyRegistryPanel model={model.strategyRegistry} />
            <StrategyDecisionMatrix model={model.strategyMatrix} />
          </div>
        </SectionFrame>

        <MatchingOrderBookPanel orderbook={model.orderbook} />

        {model.summaryError ? (
          <DiagnosticDrawer title={t('workspace.execution.diagnostics')} summary={model.summaryError.message}>
            <pre className="diagnostic-pre">{JSON.stringify(model.summaryError, null, 2)}</pre>
          </DiagnosticDrawer>
        ) : null}
        <SectionFrame
          title={t('execution.timeline')}
          description={t('workspace.execution.timelineDescription')}
          className="timeline-section"
        >
          <ExecutionTimelinePanel active={active} />
        </SectionFrame>
      </div>
    </div>
  )
}
