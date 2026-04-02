import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, EmptyState, GlassPanel, PanelSection, StatusPill, TerminalBand } from '../../../ui'
import type { ExecutionOperationsPanelModel } from '../view-models'

type Props = {
  model: ExecutionOperationsPanelModel
}

export function ExecutionOperationsPanel({ model }: Props) {
  const { t } = useI18n()

  const toneClassName = (tone?: 'default' | 'muted' | 'accent') =>
    tone === 'accent'
      ? 'obs-value obs-value-bid'
      : 'obs-value'

  if (model.headlineItems.length === 0) {
    return (
      <GlassPanel className="xo-panel" tone="subtle">
        <TerminalBand model={model.band} className="xo-band" compact />
        <EmptyState
          title={model.emptyTitle ?? model.summary}
          body={model.emptyHint ?? t('workspace.execution.operationsDescription')}
        />
      </GlassPanel>
    )
  }

  return (
    <GlassPanel className="xo-panel" tone="subtle">
      <TerminalBand model={model.band} className="xo-band" compact />

      <PanelSection
        className="xo-section"
        eyebrow={t('workspace.execution.operationsTitle')}
        title={t('workspace.execution.operationsHeadlineTitle')}
        hint={t('workspace.execution.operationsFlowHint')}
      >
        <div className="obs-grid" role="list" aria-label={t('workspace.execution.operationsHeadlineTitle')}>
          {model.headlineItems.map((item) => (
            <article key={item.id} role="listitem" className="sd-card">
              <p className="subtle-label">{item.label}</p>
              <p className={toneClassName(item.tone)}>{item.value}</p>
            </article>
          ))}
        </div>
      </PanelSection>

      <div className="ids-grid">
        <PanelSection
          className="xo-section"
          title={t('workspace.execution.operationsLatencyTitle')}
          hint={t('workspace.execution.operationsLatencyHint')}
        >
          <DataList items={model.latencyItems} dense />
        </PanelSection>

        <PanelSection
          className="xo-section"
          title={t('workspace.execution.operationsVenueTitle')}
          hint={t('workspace.execution.operationsVenueHint')}
        >
          <DataList items={model.venueItems} dense />
        </PanelSection>
      </div>

      {model.lifecycleSummary.length > 0 ? (
        <div className="ids-grid">
          <PanelSection
            className="xo-section"
            title={t('workspace.execution.lifecycleDistributionTitle')}
            hint={t('workspace.execution.operationsFlowHint')}
          >
            <DataList items={model.lifecycleSummary} dense />
          </PanelSection>

          {model.reasonSummary.length > 0 ? (
            <PanelSection
              className="xo-section"
              title={t('workspace.execution.reasonDistributionTitle')}
              hint={t('workspace.execution.operationsReasonHint')}
              bodyClassName="exec-scroll-list"
            >
                <DataList items={model.reasonSummary} dense />
            </PanelSection>
          ) : null}
        </div>
      ) : null}

      <PanelSection
        className="xo-section xo-diagnosis"
        title={t('workspace.execution.diagnosisTitle')}
        hint={model.diagnosisHint}
        aside={
          <StatusPill
            state={model.diagnosisTone === 'danger' ? 'error' : model.diagnosisTone === 'accent' ? 'degraded' : 'idle'}
            label={model.diagnosisLabel}
            compact
          />
        }
      >
        <p className="sp-summary">{model.diagnosisLabel}</p>
      </PanelSection>

      {model.accountSummary.length > 0 ? (
        <PanelSection
          className="xo-section"
          title={t('workspace.execution.accountSummary')}
          hint={t('workspace.execution.accountSummaryHint')}
          bodyClassName="exec-scroll-list"
        >
            <DataList items={model.accountSummary} dense />
        </PanelSection>
      ) : null}

      <PanelSection
        className="xo-section xo-alerts"
        title={t('workspace.execution.operationsAnomalies')}
        hint={t('workspace.execution.operationsReasonHint')}
      >
        {model.anomalies.length > 0 ? (
          <ul className="xo-alert-list">
            {model.anomalies.map((item) => (
              <li key={item} className="xo-alert">
                {item}
              </li>
            ))}
          </ul>
        ) : (
          <p className="xo-empty">{t('workspace.execution.operationsNoAnomalies')}</p>
        )}
      </PanelSection>
    </GlassPanel>
  )
}
