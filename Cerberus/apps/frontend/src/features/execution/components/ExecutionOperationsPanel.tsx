import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, EmptyState, GlassPanel, StatusPill } from '../../../ui'
import type { ExecutionOperationsPanelModel } from '../view-models'

type Props = {
  model: ExecutionOperationsPanelModel
}

export function ExecutionOperationsPanel({ model }: Props) {
  const { t } = useI18n()

  if (model.items.length === 0) {
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

      <DataList items={model.items} dense />

      {model.lifecycleSummary.length > 0 ? (
        <div className="xo-lifecycle">
          <p className="subtle-label">{t('workspace.execution.lifecycleDistributionTitle')}</p>
          <DataList items={model.lifecycleSummary} dense />
        </div>
      ) : null}

      {model.reasonSummary.length > 0 ? (
        <div className="xo-lifecycle">
          <p className="subtle-label">{t('workspace.execution.reasonDistributionTitle')}</p>
          <DataList items={model.reasonSummary} dense />
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
        <div className="eas">
          <p className="subtle-label">{t('workspace.execution.accountSummary')}</p>
          <DataList items={model.accountSummary} dense />
        </div>
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
