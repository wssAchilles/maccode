import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, PanelSection, StatusPill, TerminalBand } from '../../../ui'
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
      <TerminalBand model={model.band} className="if-band" compact />
      <div className="health-grid">
        <PanelSection
          className="ifp"
          eyebrow={t('workspace.inference.runtimeStatus')}
          title={model.summary}
          hint={model.reason ?? t('workspace.inference.description')}
          aside={<StatusPill state={model.state} label={model.stateLabel} compact />}
        >
          <DataList items={model.runtimeItems} />
          {model.reason ? (
            <p className="ip-reason" role="alert">
              {t('workspace.inference.reason')}: {model.reason}
            </p>
          ) : null}
        </PanelSection>

        <PanelSection
          className="ifp"
          eyebrow={t('workspace.inference.rolloutSummary')}
          title={model.rolloutItems[0]?.value ?? model.stateLabel}
          hint={t('workspace.inference.description')}
        >
          <DataList items={model.rolloutItems} />
        </PanelSection>

        <PanelSection
          className="ifp"
          eyebrow={t('workspace.inference.comparisonSummary')}
          title={model.symbolBand.title}
          hint={t('workspace.inference.symbolComparison')}
        >
          <DataList items={model.comparisonItems} />
        </PanelSection>

        <PanelSection
          className="ifp"
          eyebrow={t('workspace.inference.model')}
          title={model.summary}
          hint={t('workspace.inference.model')}
        >
          <DataList items={model.modelItems} />
        </PanelSection>

        <PanelSection
          className="ifp"
          eyebrow={t('workspace.inference.recentAudit')}
          title={model.auditBand.title}
          hint={model.auditBand.hint}
        >
          <DataList items={model.auditItems} />
        </PanelSection>
      </div>

      <div className="idt-grid">
        <InferenceSymbolComparisonPanel model={model} />
        <InferenceAuditTimeline model={model} />
      </div>
    </div>
  )
}
