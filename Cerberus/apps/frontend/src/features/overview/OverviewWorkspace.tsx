import { useI18n } from '../../i18n/I18nProvider'
import type { WorkspaceId } from '../../store/slices/shared'
import { DataList, GlassPanel, InlineAlert, MetricTile, SectionFrame, StatusPill } from '../../ui'
import { CoreFlowPanel } from '../../components/CoreFlowPanel'
import { formatConfidence } from '../../view-models/workbench'
import { useOverviewWorkspaceModel } from './useOverviewWorkspaceModel'
import { InferenceStatusCard } from '../inference-observability/components/InferenceStatusCard'

type Props = {
  active?: boolean
  onSelectWorkspace: (workspace: WorkspaceId) => void
}

export function OverviewWorkspace({ active: _active = true, onSelectWorkspace }: Props) {
  const { t } = useI18n()
  const model = useOverviewWorkspaceModel({ onSelectWorkspace })

  return (
    <div className="workspace-grid">
      <SectionFrame
        title={t('workspace.overview.title')}
        description={t('workspace.overview.description')}
        eyebrow={t('workspace.overview.eyebrow')}
        aside={
          <div className="workspace-actions">
            <button type="button" className="soft-button soft-button-primary" onClick={model.openExecution}>
              {t('workspace.cta.execution')}
            </button>
            <button type="button" className="soft-button" onClick={model.openHealth}>
              {t('workspace.cta.health')}
            </button>
          </div>
        }
        className="workspace-span-full"
        tone="hero"
      >
        <div className="metric-grid">
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
      </SectionFrame>

      {model.summaryError ? (
        <InlineAlert title={t('workspace.overview.attention')} tone="warning" className="workspace-span-full">
          {model.summaryError.message}
        </InlineAlert>
      ) : null}

      <div className="workspace-main">
        <CoreFlowPanel />
      </div>

      <div className="workspace-side stack">
        <SectionFrame title={t('workspace.overview.healthDigest')} description={t('workspace.health.description')}>
          <div className="stack-sm">
            {model.healthCards.map((card) => (
              <GlassPanel key={card.id} className="health-digest-card" tone="subtle">
                <div className="health-digest-head">
                  <div>
                    <p className="subtle-label">{card.title}</p>
                    <p className="health-digest-meta">{card.staleLabel}</p>
                  </div>
                  <StatusPill state={card.state} label={card.stateLabel} compact />
                </div>
                <p className="health-digest-updated">{t('common.updatedAt')}: {card.updatedAt}</p>
                {card.reason ? <p className="health-digest-reason">{card.reason}</p> : null}
              </GlassPanel>
            ))}
          </div>
        </SectionFrame>

        <SectionFrame title={t('workspace.inference.title')} description={t('workspace.inference.description')}>
          <InferenceStatusCard model={model.inferenceCard} onOpenHealth={model.openHealth} />
        </SectionFrame>

        <SectionFrame title={t('strategy.recent')} description={t('workspace.overview.signalsDescription')}>
          {model.recentSignals.length === 0 ? (
            <p className="empty-inline">{t('strategy.noData')}</p>
          ) : (
            <div className="stack-sm">
              {model.recentSignals.map((signal) => (
                <GlassPanel key={`${signal.created_at}-${signal.strategy_id}`} className="signal-card" tone="subtle">
                  <div className="signal-card-head">
                    <p className="signal-card-title">{signal.signal}</p>
                    <p className="signal-card-symbol">{signal.symbol}</p>
                  </div>
                  <DataList
                    dense
                    items={[
                      { id: 'confidence', label: t('strategy.confidence'), value: formatConfidence(signal.confidence) },
                      { id: 'createdAt', label: t('common.updatedAt'), value: new Date(signal.created_at).toLocaleString() },
                    ]}
                  />
                </GlassPanel>
              ))}
            </div>
          )}
          <div className="workspace-actions">
            <button type="button" className="soft-button" onClick={model.openMarket}>
              {t('workspace.cta.market')}
            </button>
            <button type="button" className="soft-button" onClick={model.openExecution}>
              {t('workspace.cta.execution')}
            </button>
          </div>
        </SectionFrame>

        <SectionFrame title={t('strategy.persistence')} description={t('workspace.health.persistenceDescription')}>
          <DataList items={model.persistenceItems} />
        </SectionFrame>
      </div>
    </div>
  )
}
