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
      <TerminalBand model={model.band} className="if-band" compact hideHint hideEyebrow />
      <div className="health-grid">
        <PanelSection
          className="ifp"
          eyebrow={t('workspace.inference.runtimeStatus')}
          title={model.summary}
          hideEyebrow
          aside={<StatusPill state={model.state} label={model.stateLabel} compact />}
          compact
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
          hideEyebrow
          compact
        >
          <DataList items={model.rolloutItems} />
        </PanelSection>

        <PanelSection
          className="ifp"
          eyebrow={t('workspace.inference.comparisonSummary')}
          title={model.symbolBand.title}
          hideEyebrow
          compact
        >
          <DataList items={model.comparisonItems} />
        </PanelSection>

        <PanelSection
          className="ifp"
          eyebrow={t('workspace.inference.model')}
          title={model.summary}
          hideEyebrow
          compact
        >
          <DataList items={model.modelItems} />
        </PanelSection>

        <PanelSection
          className="ifp"
          eyebrow={t('workspace.inference.recentAudit')}
          title={model.auditBand.title}
          hideEyebrow
          compact
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
