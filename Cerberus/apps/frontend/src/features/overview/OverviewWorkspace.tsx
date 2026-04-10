import type { WorkspaceId } from '../../store/slices/shared'
import { WORKSPACE_MODELS } from '../../view-models/workbench'
import {
  DataList,
  DiagnosticDrawer,
  GlassPanel,
  InlineAlert,
  MetricTile,
  MotionSurface,
  PanelSection,
  RevealGroup,
  SectionFrame,
  StatusPill,
  TerminalBand,
  WorkspaceOperatorDeck,
  WorkspaceSpotlight,
} from '../../ui'
import { CoreFlowPanel } from '../../components/CoreFlowPanel'
import { useI18n } from '../../i18n/I18nProvider'
import { InferenceStatusCard } from '../inference-observability/components/InferenceStatusCard'
import { useOverviewWorkspaceModel } from './useOverviewWorkspaceModel'

type Props = {
  active?: boolean
  onSelectWorkspace: (workspace: WorkspaceId) => void
}

export function OverviewWorkspace({ active: _active = true, onSelectWorkspace }: Props) {
  const { t } = useI18n()
  const model = useOverviewWorkspaceModel({ active: _active, onSelectWorkspace })

  const workspaceShortcuts = WORKSPACE_MODELS.filter((item) => item.id !== 'overview').map((item) => ({
    ...item,
    onSelect:
      item.id === 'market'
        ? model.openMarket
        : item.id === 'book'
          ? model.openBook
          : item.id === 'strategy'
            ? model.openStrategy
            : item.id === 'execution'
              ? model.openExecution
              : item.id === 'inference'
                ? model.openInference
                : model.openHealth,
  }))

  return (
    <div className="ws-grid ws-grid-overview" data-workspace="overview">
      <div className="ws-main wsm">
        <SectionFrame
          title={t('workspace.overview.title')}
          description={t('workspace.overview.description')}
          eyebrow={t('workspace.overview.eyebrow')}
          aside={
            <div className="ws-actions">
              <button type="button" className="soft-button sbp" onClick={model.openMarket}>
                {t('workspace.cta.market')}
              </button>
              <button type="button" className="soft-button" onClick={model.openExecution}>
                {t('workspace.cta.execution')}
              </button>
              <button type="button" className="soft-button" onClick={model.openHealth}>
                {t('workspace.cta.health')}
              </button>
              {model.summaryError ? (
                <DiagnosticDrawer
                  title={t('workspace.overview.attention')}
                  summary="微服务异常日志"
                  contentClassName="tail-drawer"
                >
                  <InlineAlert title="Error Log" tone="danger">
                    {model.summaryError.message}
                  </InlineAlert>
                </DiagnosticDrawer>
              ) : null}
            </div>
          }
          tone="hero"
          accent="cyan"
          stage="hero"
        >
          <TerminalBand model={model.contextBand} className="hero-band" />
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

        <SectionFrame
          title={t('workspace.overview.operatorDeckTitle')}
          description={t('workspace.overview.operatorDeckDescription')}
          descriptionMode="srOnly"
          accent="teal"
          stage="operator"
          compactHeader
          bodyClassName="operator-shell"
        >
          <WorkspaceOperatorDeck sections={model.operatorSections} layout="rail" />
        </SectionFrame>

        <SectionFrame
          title={t('workspace.nav')}
          description={t('shell.navRail')}
          descriptionMode="srOnly"
          accent="cyan"
          stage="feature"
          compactHeader
          bodyClassName="shortcut-shell"
        >
          <div className="workspace-portal-grid workspace-portal-grid-compact">
            {workspaceShortcuts.map((item, index) => (
              <RevealGroup key={item.id} revealIndex={index} className="workspace-portal-shell">
                <MotionSurface className="workspace-portal-surface" mode="panel">
                  <button type="button" className="workspace-portal" onClick={item.onSelect}>
                    <GlassPanel className="workspace-portal-card" tone="subtle">
                      <div className="workspace-portal-head">
                        <div>
                          <p className="subtle-label">{item.indexLabel}</p>
                          <p className="workspace-portal-title">{t(item.titleKey)}</p>
                        </div>
                        <span className="workspace-portal-pulse" aria-hidden="true" />
                      </div>
                      <p className="workspace-portal-description">{t(item.descriptionKey)}</p>
                    </GlassPanel>
                  </button>
                </MotionSurface>
              </RevealGroup>
            ))}
          </div>
        </SectionFrame>

        <div className="overview-tail-grid">
          <SectionFrame
            title={t('strategy.recent')}
            description={t('workspace.overview.signalsDescription')}
            descriptionMode="srOnly"
            accent="cyan"
            stage="tail"
            compactHeader
            bodyClassName="tail-shell"
          >
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
              <button type="button" className="soft-button" onClick={model.openStrategy}>
                {t('workspace.cta.strategy')}
              </button>
              <button type="button" className="soft-button" onClick={model.openInference}>
                {t('workspace.cta.inference')}
              </button>
            </div>
          </SectionFrame>

          <SectionFrame
            title={t('strategy.persistence')}
            description={t('workspace.health.persistenceDescription')}
            descriptionMode="srOnly"
            accent="amber"
            stage="tail"
            compactHeader
            bodyClassName="tail-shell"
          >
            <PanelSection
              className="tail-card"
              eyebrow={t('strategy.persistence')}
              title={t('workspace.health.persistenceTitle')}
              hint={t('workspace.health.persistenceDescription')}
              compact
            >
              <DataList items={model.persistenceItems} />
            </PanelSection>
            <div className="ws-actions">
              <button type="button" className="soft-button" onClick={model.openBook}>
                {t('workspace.cta.book')}
              </button>
            </div>
          </SectionFrame>
        </div>
      </div>

      <div className="ws-side stack wss">
        <CoreFlowPanel active={_active} />

        <SectionFrame
          title={t('workspace.overview.healthDigest')}
          description={t('workspace.health.description')}
          descriptionMode="srOnly"
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
          descriptionMode="srOnly"
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
