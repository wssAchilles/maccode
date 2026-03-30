import { useI18n } from '../../../i18n/I18nProvider'
import { EmptyState, GlassPanel } from '../../../ui'
import type { StrategyDecisionMatrixModel } from '../view-models'

type Props = {
  model: StrategyDecisionMatrixModel
}

export function StrategyDecisionMatrix({ model }: Props) {
  const { t } = useI18n()

  if (model.items.length === 0) {
    return (
      <GlassPanel className="strategy-panel strategy-panel-empty" tone="subtle">
        <EmptyState title={model.emptyTitle ?? model.summary} body={model.emptyHint ?? model.hint} />
      </GlassPanel>
    )
  }

  return (
    <GlassPanel className="strategy-panel" tone="subtle">
      <div className="strategy-panel-head">
        <div>
          <p className="subtle-label">{t('workspace.strategy.matrixTitle')}</p>
          <p className="strategy-panel-summary">{model.summary}</p>
          <p className="strategy-panel-hint">{model.hint}</p>
        </div>
        {model.signalId ? <p className="strategy-panel-signal-id">rid: {model.signalId}</p> : null}
      </div>

      <div className="strategy-decision-list">
        {model.items.map((item) => (
          <article
            key={item.id}
            className={item.active ? 'strategy-decision-card strategy-decision-card-active' : 'strategy-decision-card'}
          >
            <div className="strategy-decision-head">
              <div>
                <p className="strategy-decision-title">{item.label}</p>
                <p className="strategy-decision-engine">{item.engine}</p>
              </div>
              <p className={item.tone ? `strategy-decision-signal strategy-decision-signal-${item.tone}` : 'strategy-decision-signal'}>
                {item.signal}
              </p>
            </div>

            <dl className="strategy-decision-meta">
              <div>
                <dt>{t('strategy.confidence')}</dt>
                <dd>{item.confidence}</dd>
              </div>
              <div>
                <dt>{t('workspace.strategy.weight')}</dt>
                <dd>{item.weight}</dd>
              </div>
              <div>
                <dt>{t('workspace.strategy.priority')}</dt>
                <dd>{item.priority}</dd>
              </div>
              <div>
                <dt>{t('workspace.strategy.role')}</dt>
                <dd>{item.role}</dd>
              </div>
            </dl>

            <p className="strategy-decision-source">{item.source}</p>
            {item.reason ? <p className="strategy-decision-reason">{item.reason}</p> : null}
          </article>
        ))}
      </div>
    </GlassPanel>
  )
}
