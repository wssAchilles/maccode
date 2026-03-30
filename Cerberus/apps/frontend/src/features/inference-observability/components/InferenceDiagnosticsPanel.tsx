import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, GlassPanel, StatusPill } from '../../../ui'
import type { InferenceDiagnosticsModel } from '../view-models'

type Props = {
  model: InferenceDiagnosticsModel
}

export function InferenceDiagnosticsPanel({ model }: Props) {
  const { t } = useI18n()

  return (
    <div className="health-grid">
      <GlassPanel tone="subtle" className="inference-panel">
        <div className="inference-card-head">
          <div>
            <p className="subtle-label">{t('workspace.inference.runtimeStatus')}</p>
            <p className="inference-card-summary">{model.summary}</p>
          </div>
          <StatusPill state={model.state} label={model.stateLabel} compact />
        </div>
        <DataList items={model.runtimeItems} />
        {model.reason ? (
          <p className="inference-panel-reason" role="alert">
            {t('workspace.inference.reason')}: {model.reason}
          </p>
        ) : null}
      </GlassPanel>

      <GlassPanel tone="subtle" className="inference-panel">
        <p className="subtle-label">{t('workspace.inference.model')}</p>
        <p className="inference-card-summary">{model.summary}</p>
        <DataList items={model.modelItems} />
      </GlassPanel>
    </div>
  )
}
