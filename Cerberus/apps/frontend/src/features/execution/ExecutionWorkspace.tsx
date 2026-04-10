import { Suspense } from 'react'

import {
  LazyExecutionConsole,
  LazyExecutionTimelinePanel,
  PanelSkeleton,
} from '../../app/lazyPanels'
import { useI18n } from '../../i18n/I18nProvider'
import type { WorkspaceId } from '../../store/slices/shared'
import { DiagnosticDrawer, GlassPanel, SectionFrame, TerminalBand, WorkspaceOperatorDeck } from '../../ui'
import { ExecutionOperationsPanel } from './components/ExecutionOperationsPanel'
import { ExecutionLifecyclePanel } from '../strategy-orchestration/components/ExecutionLifecyclePanel'
import { useExecutionWorkspaceModel } from './useExecutionWorkspaceModel'

type Props = {
  active?: boolean
  onSelectWorkspace?: (workspace: WorkspaceId) => void
}

export function ExecutionWorkspace({ active = true, onSelectWorkspace }: Props) {
  const { t } = useI18n()
  const model = useExecutionWorkspaceModel({ active })

  return (
    <div className="ws-grid ws-grid-execution" data-workspace="execution">
      <SectionFrame
        title={t('workspace.execution.ticketTitle')}
        description={t('workspace.execution.ticketDescription')}
        descriptionMode="srOnly"
        className="ws-span-full ws-primary-panel"
        accent="amber"
        stage="feature"
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

      <div className="ws-main stack wsm">
        <SectionFrame
          title={t('workspace.execution.operatorDeckTitle')}
          description={t('workspace.execution.operatorDeckDescription')}
          descriptionMode="srOnly"
          accent="teal"
          stage="operator"
          compactHeader
          bodyClassName="operator-shell"
        >
          <WorkspaceOperatorDeck sections={model.operatorSections} layout="rail" />
        </SectionFrame>

        <SectionFrame
          title={t('workspace.execution.operationsTitle')}
          description={t('workspace.execution.operationsDescription')}
          descriptionMode="srOnly"
          accent="amber"
          stage="tail"
          compactHeader
        >
          <DiagnosticDrawer
            title={t('workspace.execution.operationsTitle')}
            summary={t('workspace.execution.operationsDescription')}
            contentClassName="tail-drawer"
          >
            <ExecutionOperationsPanel model={model.operationsPanel} />
          </DiagnosticDrawer>
        </SectionFrame>
      </div>

      <div className="ws-side stack xsd wss">
        <GlassPanel className="rail-shell" tone="subtle">
          <TerminalBand model={model.inspectorBand} className="inspector-band" compact hideHint hideEyebrow />
        </GlassPanel>
        <SectionFrame
          title={t('workspace.execution.linkageTitle')}
          description={t('workspace.execution.linkageDetail')}
          descriptionMode="srOnly"
          bodyClassName="inspector-shell"
          accent="cyan"
          stage="inspector"
          compactHeader
        >
          <div className="stack-sm">
            <p className="empty-inline">{t('workspace.execution.linkageHint').replace('{symbol}', model.selectedSymbol)}</p>
            <div className="ws-actions">
              <button type="button" className="soft-button sbp" onClick={() => onSelectWorkspace?.('book')}>
                {t('workspace.cta.book')}
              </button>
              <button type="button" className="soft-button" onClick={() => onSelectWorkspace?.('market')}>
                {t('workspace.cta.market')}
              </button>
              <button type="button" className="soft-button" onClick={() => onSelectWorkspace?.('strategy')}>
                {t('workspace.cta.strategy')}
              </button>
            </div>
          </div>
        </SectionFrame>

        {model.summaryError ? (
          <DiagnosticDrawer title={t('workspace.execution.diagnostics')} summary={model.summaryError.message}>
            <pre className="diagnostic-pre">{JSON.stringify(model.summaryError, null, 2)}</pre>
          </DiagnosticDrawer>
        ) : null}
        <SectionFrame
          title={t('execution.timeline')}
          description={t('workspace.execution.timelineDescription')}
          descriptionMode="srOnly"
          className="xts"
          accent="cyan"
          stage="tail"
          compactHeader
          bodyClassName="tail-shell"
        >
          <DiagnosticDrawer
            title={t('execution.timeline')}
            summary={t('workspace.execution.timelineDescription')}
            testId="execution-timeline-drawer"
          >
            <Suspense fallback={<PanelSkeleton height="320px" />}>
              <LazyExecutionTimelinePanel active={active} />
            </Suspense>
          </DiagnosticDrawer>
        </SectionFrame>
      </div>

      <SectionFrame
        title={t('workspace.execution.lifecycleTitle')}
        description={t('workspace.execution.lifecycleDescription')}
        descriptionMode="srOnly"
        className="ws-span-full"
        accent="cyan"
        stage="tail"
        compactHeader
      >
        <DiagnosticDrawer
          title={t('workspace.execution.lifecycleTitle')}
          summary={t('workspace.execution.lifecycleDescription')}
          contentClassName="tail-drawer"
        >
          <ExecutionLifecyclePanel model={model.lifecyclePanel} />
        </DiagnosticDrawer>
      </SectionFrame>
    </div>
  )
}
