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
      <GlassPanel className="execution-operations-panel" tone="subtle">
        <EmptyState
          title={model.emptyTitle ?? model.summary}
          body={model.emptyHint ?? t('workspace.execution.operationsDescription')}
        />
      </GlassPanel>
    )
  }

  return (
    <GlassPanel className="execution-operations-panel" tone="subtle">
      <div className="strategy-panel-head">
        <div>
          <p className="subtle-label">{t('workspace.execution.operationsTitle')}</p>
          <p className="strategy-panel-summary">{model.summary}</p>
        </div>
        <StatusPill state={model.state} label={model.stateLabel} compact />
      </div>

      <DataList items={model.items} dense />

      <div className="execution-operations-alerts">
        <p className="subtle-label">{t('workspace.execution.operationsAnomalies')}</p>
        {model.anomalies.length > 0 ? (
          <ul className="execution-operations-alert-list">
            {model.anomalies.map((item) => (
              <li key={item} className="execution-operations-alert">
                {item}
              </li>
            ))}
          </ul>
        ) : (
          <p className="execution-operations-empty">{t('workspace.execution.operationsNoAnomalies')}</p>
        )}
      </div>
    </GlassPanel>
  )
}
