import { useI18n } from '../../i18n/I18nProvider'
import type { WorkspaceId } from '../../store/slices/shared'
import {
  DataList,
  DiagnosticDrawer,
  InlineAlert,
  MetricTile,
  PanelSection,
  SectionFrame,
  StatusPill,
  TerminalBand,
  WorkspaceOperatorDeck,
  WorkspaceSpotlight,
} from '../../ui'
import { CoreFlowPanel } from '../../components/CoreFlowPanel'
import { useOverviewWorkspaceModel } from './useOverviewWorkspaceModel'
import { InferenceStatusCard } from '../inference-observability/components/InferenceStatusCard'
import { StrategyOrchestrationAuditTimeline } from '../strategy-orchestration/components/StrategyOrchestrationAuditTimeline'
import { StrategyDecisionMatrix } from '../strategy-orchestration/components/StrategyDecisionMatrix'
import { StrategyPortfolioPanel } from '../strategy-orchestration/components/StrategyPortfolioPanel'
import { StrategyRegistryPanel } from '../strategy-orchestration/components/StrategyRegistryPanel'

type Props = {
  active?: boolean
  onSelectWorkspace: (workspace: WorkspaceId) => void
}

export function OverviewWorkspace({ active: _active = true, onSelectWorkspace }: Props) {
  const { t } = useI18n()
  const model = useOverviewWorkspaceModel({ active: _active, onSelectWorkspace })

  return (
    <div className="ws-grid ws-grid-overview" data-workspace="overview">
      <div className="ws-main wsm">
        <SectionFrame
          title={t('workspace.overview.title')}
          description={t('workspace.overview.description')}
          eyebrow={t('workspace.overview.eyebrow')}
          aside={
            <div className="ws-actions">
              <button type="button" className="soft-button sbp" onClick={model.openExecution}>
                {t('workspace.cta.execution')}
              </button>
              <button type="button" className="soft-button" onClick={model.openHealth}>
                {t('workspace.cta.health')}
              </button>
              {model.summaryError && (
                <DiagnosticDrawer
                  title={t('workspace.overview.attention')}
                  summary="微服务异常日志"
                  contentClassName="tail-drawer"
                >
                  <InlineAlert title="Error Log" tone="danger">
                    {model.summaryError.message}
                  </InlineAlert>
                </DiagnosticDrawer>
              )}
            </div>
          }
          tone="hero"
          accent="cyan"
          stage="hero"
        >
          <TerminalBand model={model.contextBand} className="hero-band" />
          <div className="ws-hero-grid">
            <WorkspaceSpotlight model={model.spotlight} className="ws-hero-spotlight" />
            <div className="ws-hero-side">
              <div className="metric-grid ws-hero-metrics">
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
            </div>
          </div>
        </SectionFrame>

        <SectionFrame
          title={t('workspace.overview.operatorDeckTitle')}
          description={t('workspace.overview.operatorDeckDescription')}
          accent="teal"
          stage="operator"
          compactHeader
          bodyClassName="operator-shell"
        >
          <WorkspaceOperatorDeck sections={model.operatorSections} layout="rail" />
        </SectionFrame>

        <SectionFrame
          title={t('workspace.strategy.title')}
          description={t('workspace.strategy.description')}
          accent="teal"
          stage="feature"
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

        <div className="overview-tail-grid">
          <SectionFrame title={t('strategy.recent')} description={t('workspace.overview.signalsDescription')} accent="cyan" stage="tail" compactHeader bodyClassName="tail-shell">
            <TerminalBand model={model.tailBand} className="tail-band" compact hideHint hideEyebrow />
            {model.recentSignals.length === 0 ? (
              <p className="empty-inline">{t('strategy.noData')}</p>
            ) : (
              <div className="stack-sm">
                {model.recentSignals.map((signal) => (
                  <PanelSection
                    key={signal.id}
                    className="signal-card"
                    eyebrow={signal.eyebrow}
                    title={signal.title}
                    hint={`${t('common.updatedAt')}: ${signal.hint}`}
                    compact
                  >
                    <DataList dense items={signal.items} />
                  </PanelSection>
                ))}
              </div>
            )}
            <div className="ws-actions">
              <button type="button" className="soft-button" onClick={model.openMarket}>
                {t('workspace.cta.market')}
              </button>
            </div>
          </SectionFrame>

          <SectionFrame title={t('strategy.persistence')} description={t('workspace.health.persistenceDescription')} accent="amber" stage="tail" compactHeader bodyClassName="tail-shell">
            <PanelSection
              className="tail-card"
              eyebrow={t('strategy.persistence')}
              title={t('workspace.health.persistenceTitle')}
              hint={t('workspace.health.persistenceDescription')}
              compact
            >
              <DataList items={model.persistenceItems} />
            </PanelSection>
          </SectionFrame>
        </div>
      </div>

      <div className="ws-side stack wss">
        <CoreFlowPanel active={_active} />

        <SectionFrame
          title={t('workspace.overview.healthDigest')}
          description={t('workspace.health.description')}
          accent="amber"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
          <div className="stack-sm">
            <TerminalBand model={model.healthDigestBand} className="overview-health-band" compact hideHint hideEyebrow />
            {model.healthCards.map((card) => (
              <PanelSection
                key={card.id}
                className="hd-card"
                eyebrow={card.title}
                title={card.stateLabel}
                hint={`${card.staleLabel} · ${t('common.updatedAt')}: ${card.updatedAt}`}
                aside={<StatusPill state={card.state} label={card.stateLabel} compact />}
                compact
              >
                <DataList
                  dense
                  items={[
                    { id: 'request', label: t('health.requestId'), value: card.requestId ?? t('common.na') },
                    { id: 'reason', label: t('workspace.inference.reason'), value: card.reason ?? t('common.na') },
                  ]}
                />
              </PanelSection>
            ))}
          </div>
        </SectionFrame>

        <SectionFrame
          title={t('workspace.inference.title')}
          description={t('workspace.inference.description')}
          accent="teal"
          stage="inspector"
          compactHeader
          bodyClassName="inspector-shell"
        >
          <TerminalBand model={model.inferenceBand} className="inspector-band" compact hideHint hideEyebrow />
          <InferenceStatusCard model={model.inferenceCard} onOpenHealth={model.openHealth} />
        </SectionFrame>
      </div>
    </div>
  )
}
