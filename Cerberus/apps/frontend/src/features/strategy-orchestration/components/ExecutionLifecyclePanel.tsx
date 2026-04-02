import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, PanelSection, StatusPill, TerminalBand } from '../../../ui'
import type { ExecutionLifecyclePanelModel } from '../view-models'

type Props = {
  model: ExecutionLifecyclePanelModel
}

export function ExecutionLifecyclePanel({ model }: Props) {
  const { t } = useI18n()

  const toneClassName = (tone?: 'default' | 'muted' | 'accent') =>
    tone === 'accent'
      ? 'obs-value obs-value-bid'
      : 'obs-value'

  return (
    <div className="xl-panel">
      <TerminalBand model={model.band} className="xtl" compact />
      <PanelSection
        className="xl-stage-section"
        eyebrow={t('workspace.execution.lifecycleTitle')}
        title={model.summary}
        hint={t('workspace.execution.lifecycleDescription')}
        aside={<StatusPill state={model.state} label={model.stateLabel} compact />}
      >
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
      </PanelSection>

      <PanelSection
        className="xl-metrics-section"
        eyebrow={t('workspace.execution.lifecycleDistributionTitle')}
        title={t('workspace.execution.lifecycleTitle')}
        hint={t('workspace.execution.lifecycleDescription')}
      >
        <div className="obs-grid" role="list" aria-label={t('workspace.execution.lifecycleTitle')}>
          {model.summaryItems.map((item) => (
            <article key={item.id} role="listitem" className="sd-card">
              <p className="subtle-label">{item.label}</p>
              <p className={toneClassName(item.tone)}>{item.value}</p>
            </article>
          ))}
        </div>
      </PanelSection>

      <div className="ids-grid">
        <PanelSection
          className="xl-detail-section"
          eyebrow={t('workspace.execution.lifecycleIdentifiersTitle')}
          title={t('workspace.execution.lifecycleIdentifiersTitle')}
          hint={t('workspace.execution.lifecycleIdentifiersHint')}
        >
          <div className="exec-scroll-list exec-identity-list">
            <DataList items={model.identifierItems} dense />
          </div>
        </PanelSection>

        <PanelSection
          className="xl-detail-section"
          eyebrow={t('workspace.execution.lifecycleTelemetryTitle')}
          title={t('workspace.execution.lifecycleTelemetryTitle')}
          hint={t('workspace.execution.lifecycleTelemetryHint')}
        >
          <div className="exec-scroll-list">
            <DataList items={model.telemetryItems} dense />
          </div>
        </PanelSection>
      </div>

      {model.reason ? (
        <p className="xl-reason" role="alert">
          {model.reason}
        </p>
      ) : null}
    </div>
  )
}
