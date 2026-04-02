import { useI18n } from '../../../i18n/I18nProvider'
import { EmptyState, GlassPanel, PanelSection, TerminalBand } from '../../../ui'
import type { StrategyOrchestrationAuditTimelineModel } from '../view-models'

type Props = {
  model: StrategyOrchestrationAuditTimelineModel
}

export function StrategyOrchestrationAuditTimeline({ model }: Props) {
  const { t } = useI18n()

  if (model.items.length === 0) {
    return (
      <GlassPanel className="so-audit-panel" tone="subtle">
        {model.band ? <TerminalBand model={model.band} className="sp-band" /> : null}
        <EmptyState
          title={model.emptyTitle ?? model.summary}
          body={model.emptyHint ?? t('workspace.strategy.auditTimelineHint')}
        />
      </GlassPanel>
    )
  }

  return (
    <GlassPanel className="so-audit-panel" tone="subtle">
      {model.band ? <TerminalBand model={model.band} className="sp-band" /> : null}
      <PanelSection
        className="so-audit-section"
        eyebrow={t('workspace.strategy.auditTimelineTitle')}
        title={model.summary}
        hint={t('workspace.strategy.auditTimelineHint')}
      />

      <div className="so-audit-list" role="list" aria-label={t('workspace.strategy.auditTimelineTitle')}>
        {model.items.map((item) => (
          <article key={item.id} className="so-audit-row" role="listitem">
            <div className="so-audit-main">
              <p className="so-audit-title">{item.title}</p>
              <p className="so-audit-message">{item.message}</p>
              {item.detail ? <p className="so-audit-detail">{item.detail}</p> : null}
            </div>
            <p className="so-audit-time">{item.createdAt}</p>
          </article>
        ))}
      </div>
    </GlassPanel>
  )
}
