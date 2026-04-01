import { useI18n } from '../../../i18n/I18nProvider'
import { EmptyState, GlassPanel } from '../../../ui'
import type { StrategyOrchestrationAuditTimelineModel } from '../view-models'

type Props = {
  model: StrategyOrchestrationAuditTimelineModel
}

export function StrategyOrchestrationAuditTimeline({ model }: Props) {
  const { t } = useI18n()

  if (model.items.length === 0) {
    return (
      <GlassPanel className="strategy-orchestration-audit-panel" tone="subtle">
        <EmptyState
          title={model.emptyTitle ?? model.summary}
          body={model.emptyHint ?? t('workspace.strategy.auditTimelineHint')}
        />
      </GlassPanel>
    )
  }

  return (
    <GlassPanel className="strategy-orchestration-audit-panel" tone="subtle">
      <div className="strategy-panel-head">
        <div>
          <p className="subtle-label">{t('workspace.strategy.auditTimelineTitle')}</p>
          <p className="strategy-panel-summary">{model.summary}</p>
        </div>
      </div>

      <div className="strategy-orchestration-audit-list" role="list" aria-label={t('workspace.strategy.auditTimelineTitle')}>
        {model.items.map((item) => (
          <article key={item.id} className="strategy-orchestration-audit-row" role="listitem">
            <div className="strategy-orchestration-audit-main">
              <p className="strategy-orchestration-audit-title">{item.title}</p>
              <p className="strategy-orchestration-audit-message">{item.message}</p>
              {item.detail ? <p className="strategy-orchestration-audit-detail">{item.detail}</p> : null}
            </div>
            <p className="strategy-orchestration-audit-time">{item.createdAt}</p>
          </article>
        ))}
      </div>
    </GlassPanel>
  )
}
