import type { WorkspaceId, WorkspacePanelId } from '../../store/slices/shared'
import { WORKSPACE_PANELS_BY_WORKSPACE } from '../../view-models/workbench'
import {
  DataList,
  DiagnosticDrawer,
  FocusedWorkspacePanel,
  InlineAlert,
  MetricTile,
  PanelSection,
  SectionFrame,
  StatusPill,
  SubpageLauncher,
  type SubpageLauncherItem,
  TerminalBand,
} from '../../ui'
import { CoreFlowPanel } from '../../components/CoreFlowPanel'
import { useI18n } from '../../i18n/I18nProvider'
import { InferenceStatusCard } from '../inference-observability/components/InferenceStatusCard'
import { useOverviewWorkspaceModel } from './useOverviewWorkspaceModel'

type Props = {
  active?: boolean
  onSelectWorkspace: (workspace: WorkspaceId) => void
  panel?: WorkspacePanelId
  onSelectPanel?: (panel: WorkspacePanelId) => void
}

export function OverviewWorkspace({
  active: _active = true,
  onSelectWorkspace,
  panel = 'home',
  onSelectPanel,
}: Props) {
  const { t } = useI18n()
  const model = useOverviewWorkspaceModel({ active: _active, onSelectWorkspace })

  const panelItems: SubpageLauncherItem[] = WORKSPACE_PANELS_BY_WORKSPACE.overview
    .filter((item) => item.id !== 'home')
    .map((item) => ({
      id: item.id,
      title: t(item.titleKey),
      description: t(item.descriptionKey),
      cta: `${t(item.actionKey)} ${t(item.titleKey)}`,
    }))

  const openHome = () => onSelectPanel?.('home')
  const openPanel = (next: string) => onSelectPanel?.(next as WorkspacePanelId)

  if (panel === 'flow') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.overview.title')}
        title={t('flow.title')}
        description={t('workspace.panel.overview.flowDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
        <CoreFlowPanel active={_active} />
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'signals') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.overview.title')}
        title={t('strategy.recent')}
        description={t('workspace.overview.signalsDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
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
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'services') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.overview.title')}
        title={t('workspace.overview.healthDigest')}
        description={t('workspace.health.description')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
        aside={
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
        }
      >
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
      </FocusedWorkspacePanel>
    )
  }

  if (panel === 'persistence') {
    return (
      <FocusedWorkspacePanel
        eyebrow={t('workspace.overview.title')}
        title={t('workspace.health.persistenceTitle')}
        description={t('workspace.health.persistenceDescription')}
        backLabel={t('workspace.panel.backHome')}
        onBack={openHome}
      >
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
        </SectionFrame>
      </FocusedWorkspacePanel>
    )
  }

  return (
    <div className="ws-grid ws-grid-overview" data-workspace="overview">
      <div className="workspace-home workspace-home-overview">
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
          className="workspace-home-main"
        >
          <TerminalBand model={model.contextBand} className="hero-band" />
          <div className="ws-home-compact-readings">
            <div className="hero-side-head">
              <p className="subtle-label">{t('workspace.hero.readings')}</p>
            </div>
            <div className="metric-grid ws-hero-metrics">
              {model.metricTiles.map((tile) => (
                <MetricTile
                  key={tile.id}
                  label={tile.label}
                  value={tile.value}
                  tone={tile.tone}
                  hint={tile.hint}
                  className="hero-metric"
                />
              ))}
            </div>
          </div>
        </SectionFrame>

        <SubpageLauncher
          title={t('workspace.panel.indexTitle')}
          description={t('workspace.panel.indexHint')}
          items={panelItems}
          onSelect={openPanel}
        />
      </div>
    </div>
  )
}
