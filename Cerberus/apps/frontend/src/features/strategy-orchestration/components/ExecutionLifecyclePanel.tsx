import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, GlassPanel, StatusPill } from '../../../ui'
import type { ExecutionLifecyclePanelModel } from '../view-models'

type Props = {
  model: ExecutionLifecyclePanelModel
}

export function ExecutionLifecyclePanel({ model }: Props) {
  const { t } = useI18n()

  return (
    <GlassPanel className="execution-lifecycle-panel" tone="subtle">
      <div className="strategy-panel-head">
        <div>
          <p className="subtle-label">{t('workspace.execution.lifecycleTitle')}</p>
          <p className="strategy-panel-summary">{model.summary}</p>
        </div>
        <StatusPill state={model.state} label={model.stateLabel} compact />
      </div>

      <div className="execution-lifecycle-stages" role="list" aria-label={t('workspace.execution.lifecycleTitle')}>
        {model.stages.map((stage) => (
          <article
            key={stage.id}
            role="listitem"
            className={`execution-lifecycle-stage execution-lifecycle-stage-${stage.state}`}
          >
            <p className="execution-lifecycle-stage-label">{stage.label}</p>
            <p className="execution-lifecycle-stage-detail">{stage.detail}</p>
          </article>
        ))}
      </div>

      <DataList items={model.items} />

      {model.reason ? (
        <p className="execution-lifecycle-reason" role="alert">
          {model.reason}
        </p>
      ) : null}
    </GlassPanel>
  )
}
