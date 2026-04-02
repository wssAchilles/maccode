import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, GlassPanel, StatusPill } from '../../../ui'
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

      <div className="obs-grid" role="list" aria-label={t('workspace.execution.lifecycleTitle')}>
        {model.summaryItems.map((item) => (
          <article key={item.id} role="listitem" className="sd-card">
            <p className="subtle-label">{item.label}</p>
            <p className={toneClassName(item.tone)}>{item.value}</p>
          </article>
        ))}
      </div>

      <div className="ids-grid">
        <section className="sd-card">
          <div className="ids-group">
            <p className="subtle-label">{t('workspace.execution.lifecycleIdentifiersTitle')}</p>
            <p className="sp-hint">{t('workspace.execution.lifecycleIdentifiersHint')}</p>
          </div>

          <div className="exec-scroll-list exec-identity-list">
            <DataList items={model.identifierItems} dense />
          </div>
        </section>

        <section className="sd-card">
          <div className="ids-group">
            <p className="subtle-label">{t('workspace.execution.lifecycleTelemetryTitle')}</p>
            <p className="sp-hint">{t('workspace.execution.lifecycleTelemetryHint')}</p>
          </div>

          <div className="exec-scroll-list">
            <DataList items={model.telemetryItems} dense />
          </div>
        </section>
      </div>

      {model.reason ? (
        <p className="xl-reason" role="alert">
          {model.reason}
        </p>
      ) : null}
    </GlassPanel>
  )
}
