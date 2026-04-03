import { useI18n } from '../../../i18n/I18nProvider'
import { PanelSection, TerminalBand } from '../../../ui'
import type { InferenceDiagnosticsModel } from '../view-models'

type Props = {
  model: InferenceDiagnosticsModel
}

export function InferenceAuditTimeline({ model }: Props) {
  const { t } = useI18n()

  return (
    <div className="stack ip-detail">
      <TerminalBand model={model.auditBand} className="if-sub-band" compact hideHint hideEyebrow />
      <PanelSection
        className="ifp ip-detail-section"
        eyebrow={t('workspace.inference.auditTimeline')}
        title={model.auditBand.title}
        hideEyebrow
        compact
      >
        {model.auditTimeline.length > 0 ? (
          <div className="iad-list">
            {model.auditTimeline.map((entry) => (
              <div key={entry.id} className="iad-row">
                <div className="iad-copy">
                  <p className="iad-title">{entry.title}</p>
                  <p className="iad-message">{entry.message}</p>
                  {entry.detail ? <p className="iad-detail">{entry.detail}</p> : null}
                </div>
                <p className="iad-time">{entry.createdAt}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-inline">{t('workspace.inference.auditEmpty')}</div>
        )}
      </PanelSection>
    </div>
  )
}
