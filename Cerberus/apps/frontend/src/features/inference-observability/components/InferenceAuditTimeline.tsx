import { useI18n } from '../../../i18n/I18nProvider'
import { GlassPanel } from '../../../ui'
import type { InferenceDiagnosticsModel } from '../view-models'

type Props = {
  model: InferenceDiagnosticsModel
}

export function InferenceAuditTimeline({ model }: Props) {
  const { t } = useI18n()

  return (
    <GlassPanel tone="subtle" className="inference-panel inference-panel-detail">
      <div className="inference-detail-head">
        <div>
          <p className="subtle-label">{t('workspace.inference.auditTimeline')}</p>
          <p className="inference-card-summary">{t('workspace.inference.recentAudit')}</p>
        </div>
      </div>

      {model.auditTimeline.length > 0 ? (
        <div className="inference-audit-list">
          {model.auditTimeline.map((entry) => (
            <div key={entry.id} className="inference-audit-row">
              <div className="inference-audit-copy">
                <p className="inference-audit-title">{entry.title}</p>
                <p className="inference-audit-message">{entry.message}</p>
                {entry.detail ? <p className="inference-audit-detail">{entry.detail}</p> : null}
              </div>
              <p className="inference-audit-time">{entry.createdAt}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-inline">{t('workspace.inference.auditEmpty')}</div>
      )}
    </GlassPanel>
  )
}
