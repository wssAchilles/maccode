import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, GlassPanel, StatusPill } from '../../../ui'
import type { ExecutionLifecyclePanelModel } from '../view-models'

type Props = {
  model: ExecutionLifecyclePanelModel
}

export function ExecutionLifecyclePanel({ model }: Props) {
  const { t } = useI18n()

  return (
    <GlassPanel className="xl-panel" tone="subtle">
      <div className="sp-head">
        <div>
          <p className="subtle-label">{t('workspace.execution.lifecycleTitle')}</p>
          <p className="sp-summary">{model.summary}</p>
        </div>
        <StatusPill state={model.state} label={model.stateLabel} compact />
      </div>

      <div className="xl-stages" role="list" aria-label={t('workspace.execution.lifecycleTitle')}>
        {model.stages.map((stage) => (
          <article
            key={stage.id}
            role="listitem"
            className={`xl-stage xl-stage-${stage.state}`}
          >
            <p className="xl-stage-label">{stage.label}</p>
            <p className="xl-stage-detail">{stage.detail}</p>
          </article>
        ))}
      </div>

      <DataList items={model.items} />

      {model.reason ? (
        <p className="xl-reason" role="alert">
          {model.reason}
        </p>
      ) : null}
    </GlassPanel>
  )
}
