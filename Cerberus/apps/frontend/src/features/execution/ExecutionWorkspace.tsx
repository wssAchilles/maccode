import { Suspense } from 'react'

import {
  LazyExecutionConsole,
  LazyExecutionTimelinePanel,
  LazyMatchingOrderBookPanel,
  PanelSkeleton,
} from '../../app/lazyPanels'
import { useI18n } from '../../i18n/I18nProvider'
import { DiagnosticDrawer, MetricTile, SectionFrame, WorkspaceSpotlight } from '../../ui'
import { ExecutionOperationsPanel } from './components/ExecutionOperationsPanel'
import { ExecutionLifecyclePanel } from '../strategy-orchestration/components/ExecutionLifecyclePanel'
import { StrategyOrchestrationAuditTimeline } from '../strategy-orchestration/components/StrategyOrchestrationAuditTimeline'
import { StrategyDecisionMatrix } from '../strategy-orchestration/components/StrategyDecisionMatrix'
import { StrategyOrchestrationOperationsPanel } from '../strategy-orchestration/components/StrategyOrchestrationOperationsPanel'
import { StrategyPortfolioPanel } from '../strategy-orchestration/components/StrategyPortfolioPanel'
import { StrategyRegistryPanel } from '../strategy-orchestration/components/StrategyRegistryPanel'
import { useStrategyOrchestrationOperationsModel } from '../strategy-orchestration/useStrategyOrchestrationOperationsModel'
import { useExecutionWorkspaceModel } from './useExecutionWorkspaceModel'

type Props = {
  active?: boolean
}

export function ExecutionWorkspace({ active = true }: Props) {
  const { t } = useI18n()
  const model = useExecutionWorkspaceModel({ active })
  const orchestrationOps = useStrategyOrchestrationOperationsModel(active)

  return (
    <div className="ws-grid">
      <SectionFrame
        title={t('workspace.execution.title')}
        description={t('workspace.execution.description')}
        eyebrow={t('workspace.execution.eyebrow')}
        className="ws-span-full"
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

      <div className="ws-main stack">
        <SectionFrame title={t('workspace.execution.linkageTitle')} description={t('workspace.execution.linkageHint').replace('{symbol}', model.selectedSymbol)}>
          <WorkspaceSpotlight model={model.spotlight} />
        </SectionFrame>

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

        <SectionFrame
          title={t('workspace.strategy.operationsTitle')}
          description={t('workspace.strategy.operationsDescription')}
        >
          <StrategyOrchestrationOperationsPanel
            model={orchestrationOps.model}
            drafts={orchestrationOps.drafts}
            reason={orchestrationOps.reason}
            conflictPolicy={orchestrationOps.conflictPolicy}
            downgradePolicy={orchestrationOps.downgradePolicy}
            onReasonChange={orchestrationOps.setReason}
            onConflictPolicyChange={orchestrationOps.setConflictPolicy}
            onDowngradePolicyChange={orchestrationOps.setDowngradePolicy}
            onDraftFieldChange={orchestrationOps.setDraftField}
            onSaveEntry={orchestrationOps.onSaveEntry}
            onSavePolicies={orchestrationOps.onSavePolicies}
          />
        </SectionFrame>

        <SectionFrame title={t('workspace.execution.ticketTitle')} description={t('workspace.execution.ticketDescription')}>
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

      <div className="ws-side stack execution-side">
        <SectionFrame
          title={t('workspace.strategy.matrixTitle')}
          description={t('workspace.strategy.description')}
        >
          <div className="stack">
            <StrategyPortfolioPanel model={model.portfolioPanel} onSelectSymbol={model.selectSymbol} />
            <StrategyDecisionMatrix model={model.strategyMatrix} />
            <DiagnosticDrawer
              title={t('workspace.strategy.registryTitle')}
              summary={t('workspace.strategy.registryDescription')}
            >
              <StrategyRegistryPanel model={model.strategyRegistry} />
            </DiagnosticDrawer>
            <DiagnosticDrawer
              title={t('workspace.strategy.auditTimelineTitle')}
              summary={t('workspace.strategy.auditTimelineHint')}
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
          className="timeline-section"
        >
          <Suspense fallback={<PanelSkeleton height="320px" />}>
            <LazyExecutionTimelinePanel active={active} />
          </Suspense>
        </SectionFrame>
      </div>
    </div>
  )
}
