import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, GlassPanel, StatusPill, TerminalBand } from '../../../ui'
import { InferenceAuditTimeline } from './InferenceAuditTimeline'
import { InferenceSymbolComparisonPanel } from './InferenceSymbolComparisonPanel'
import type { InferenceDiagnosticsModel } from '../view-models'

type Props = {
  model: InferenceDiagnosticsModel
}

export function InferenceDiagnosticsPanel({ model }: Props) {
  const { t } = useI18n()

  return (
    <div className="stack">
      <TerminalBand model={model.band} className="if-band" />
      <div className="health-grid">
        <GlassPanel tone="subtle" className="ifp">
          <div className="ifc-head">
            <div>
              <p className="subtle-label">{t('workspace.inference.runtimeStatus')}</p>
              <p className="ifc-summary">{model.summary}</p>
            </div>
            <StatusPill state={model.state} label={model.stateLabel} compact />
          </div>
          <DataList items={model.runtimeItems} />
          {model.reason ? (
            <p className="ip-reason" role="alert">
              {t('workspace.inference.reason')}: {model.reason}
            </p>
          ) : null}
        </GlassPanel>

        <GlassPanel tone="subtle" className="ifp">
          <p className="subtle-label">{t('workspace.inference.rolloutSummary')}</p>
          <p className="ifc-summary">{t('workspace.inference.description')}</p>
          <DataList items={model.rolloutItems} />
        </GlassPanel>

        <GlassPanel tone="subtle" className="ifp">
          <p className="subtle-label">{t('workspace.inference.comparisonSummary')}</p>
          <p className="ifc-summary">{model.summary}</p>
          <DataList items={model.comparisonItems} />
        </GlassPanel>

        <GlassPanel tone="subtle" className="ifp">
          <p className="subtle-label">{t('workspace.inference.model')}</p>
          <p className="ifc-summary">{model.summary}</p>
          <DataList items={model.modelItems} />
        </GlassPanel>

        <GlassPanel tone="subtle" className="ifp">
          <p className="subtle-label">{t('workspace.inference.recentAudit')}</p>
          <p className="ifc-summary">{t('workspace.inference.gateBlockers')}</p>
          <DataList items={model.auditItems} />
        </GlassPanel>
      </div>

      <div className="idt-grid">
        <InferenceSymbolComparisonPanel model={model} />
        <InferenceAuditTimeline model={model} />
      </div>
    </div>
  )
}
