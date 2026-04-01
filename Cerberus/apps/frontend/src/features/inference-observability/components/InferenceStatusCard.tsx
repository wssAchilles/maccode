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
    <GlassPanel className="ifc" tone="subtle">
      <div className="ifc-head">
        <div>
          <p className="subtle-label">{t('workspace.inference.title')}</p>
          <p className="ifc-summary">{model.summary}</p>
        </div>
        <StatusPill state={model.state} label={model.stateLabel} compact />
      </div>

      <DataList dense items={model.items} />

      {model.reason ? (
        <p className="ip-reason" role="alert">
          {t('workspace.inference.reason')}: {model.reason}
        </p>
      ) : null}

      <div className="ws-actions">
        <button type="button" className="soft-button" onClick={onOpenHealth}>
          {t('workspace.inference.healthCta')}
        </button>
      </div>
    </GlassPanel>
  )
}
