import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, EmptyState, GlassPanel, StatusPill } from '../../../ui'
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
        <EmptyState
          title={model.emptyTitle ?? model.summary}
          body={model.emptyHint ?? t('workspace.execution.operationsDescription')}
        />
      </GlassPanel>
    )
  }

  return (
    <GlassPanel className="xo-panel" tone="subtle">
      <div className="sp-head">
        <div>
          <p className="subtle-label">{t('workspace.execution.operationsTitle')}</p>
          <p className="sp-summary">{model.summary}</p>
        </div>
        <StatusPill state={model.state} label={model.stateLabel} compact />
      </div>

      <div className="obs-grid" role="list" aria-label={t('workspace.execution.operationsHeadlineTitle')}>
        {model.headlineItems.map((item) => (
          <article key={item.id} role="listitem" className="sd-card">
            <p className="subtle-label">{item.label}</p>
            <p className={toneClassName(item.tone)}>{item.value}</p>
          </article>
        ))}
      </div>

      <div className="ids-grid">
        <section className="sd-card">
          <div className="ids-group">
            <p className="subtle-label">{t('workspace.execution.operationsLatencyTitle')}</p>
            <p className="sp-hint">{t('workspace.execution.operationsLatencyHint')}</p>
          </div>
          <DataList items={model.latencyItems} dense />
        </section>

        <section className="sd-card">
          <div className="ids-group">
            <p className="subtle-label">{t('workspace.execution.operationsVenueTitle')}</p>
            <p className="sp-hint">{t('workspace.execution.operationsVenueHint')}</p>
          </div>
          <DataList items={model.venueItems} dense />
        </section>
      </div>

      {model.lifecycleSummary.length > 0 ? (
        <div className="ids-grid">
          <section className="sd-card">
            <div className="ids-group">
              <p className="subtle-label">{t('workspace.execution.lifecycleDistributionTitle')}</p>
              <p className="sp-hint">{t('workspace.execution.operationsFlowHint')}</p>
            </div>
            <DataList items={model.lifecycleSummary} dense />
          </section>

          {model.reasonSummary.length > 0 ? (
            <section className="sd-card">
              <div className="ids-group">
                <p className="subtle-label">{t('workspace.execution.reasonDistributionTitle')}</p>
                <p className="sp-hint">{t('workspace.execution.operationsReasonHint')}</p>
              </div>
              <div className="exec-scroll-list">
                <DataList items={model.reasonSummary} dense />
              </div>
            </section>
          ) : null}
        </div>
      ) : null}

      <div className="xo-diagnosis">
        <div className="sp-head">
          <div>
            <p className="subtle-label">{t('workspace.execution.diagnosisTitle')}</p>
            <p className="sp-summary">{model.diagnosisLabel}</p>
          </div>
          <StatusPill
            state={model.diagnosisTone === 'danger' ? 'error' : model.diagnosisTone === 'accent' ? 'degraded' : 'idle'}
            label={model.diagnosisLabel}
            compact
          />
        </div>
        <p className="sp-hint">{model.diagnosisHint}</p>
      </div>

      {model.accountSummary.length > 0 ? (
        <section className="sd-card">
          <div className="ids-group">
            <p className="subtle-label">{t('workspace.execution.accountSummary')}</p>
            <p className="sp-hint">{t('workspace.execution.accountSummaryHint')}</p>
          </div>
          <div className="exec-scroll-list">
            <DataList items={model.accountSummary} dense />
          </div>
        </section>
      ) : null}

      <div className="xo-alerts">
        <p className="subtle-label">{t('workspace.execution.operationsAnomalies')}</p>
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
      </div>
    </GlassPanel>
  )
}
