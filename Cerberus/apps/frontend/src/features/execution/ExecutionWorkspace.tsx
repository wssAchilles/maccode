import { Suspense } from 'react'

import {
  LazyExecutionConsole,
  LazyExecutionTimelinePanel,
  PanelSkeleton,
} from '../../app/lazyPanels'
import { useI18n } from '../../i18n/I18nProvider'
import type { WorkspaceId } from '../../store/slices/shared'
import { DiagnosticDrawer, GlassPanel, MetricTile, SectionFrame, TerminalBand, WorkspaceOperatorDeck, WorkspaceSpotlight } from '../../ui'
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
                  hint={tile.hint}
                  tone={tile.tone}
                  className={index === 0 ? 'hero-metric hero-metric-primary' : 'hero-metric'}
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
          title={t('workspace.execution.linkageTitle')}
          description={t('workspace.execution.linkageDetail')}
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
