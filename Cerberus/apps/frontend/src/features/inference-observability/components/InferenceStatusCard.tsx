import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, GlassPanel, StatusPill } from '../../../ui'
import type { InferenceStatusCardModel } from '../view-models'

type Props = {
  model: InferenceStatusCardModel
  onOpenHealth: () => void
}

export function InferenceStatusCard({ model, onOpenHealth }: Props) {
  const { t } = useI18n()

  return (
    <GlassPanel className="inference-card" tone="subtle">
      <div className="inference-card-head">
        <div>
          <p className="subtle-label">{t('workspace.inference.title')}</p>
          <p className="inference-card-summary">{model.summary}</p>
        </div>
        <StatusPill state={model.state} label={model.stateLabel} compact />
      </div>

      <DataList dense items={model.items} />

      {model.reason ? (
        <p className="inference-panel-reason" role="alert">
          {t('workspace.inference.reason')}: {model.reason}
        </p>
      ) : null}

      <div className="workspace-actions">
        <button type="button" className="soft-button" onClick={onOpenHealth}>
          {t('workspace.inference.healthCta')}
        </button>
      </div>
    </GlassPanel>
  )
}
