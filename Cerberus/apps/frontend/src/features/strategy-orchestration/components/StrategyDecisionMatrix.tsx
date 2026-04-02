import { useI18n } from '../../../i18n/I18nProvider'
import { EmptyState, GlassPanel, PanelSection, TerminalBand } from '../../../ui'
import type { StrategyDecisionMatrixModel } from '../view-models'

type Props = {
  model: StrategyDecisionMatrixModel
}

export function StrategyDecisionMatrix({ model }: Props) {
  const { t } = useI18n()

  if (model.items.length === 0) {
    return (
      <GlassPanel className="sp sp-empty" tone="subtle">
        {model.band ? <TerminalBand model={model.band} className="sp-band" /> : null}
        <EmptyState title={model.emptyTitle ?? model.summary} body={model.emptyHint ?? model.hint} />
      </GlassPanel>
    )
  }

  return (
    <GlassPanel className="sp" tone="subtle">
      {model.band ? <TerminalBand model={model.band} className="sp-band" /> : null}
      <PanelSection
        className="sp-section"
        eyebrow={t('workspace.strategy.matrixTitle')}
        title={model.summary}
        hint={model.hint}
        aside={model.signalId ? <p className="sp-signal-id">rid: {model.signalId}</p> : null}
      />

      <div className="sd-list" role="list" aria-label={t('workspace.strategy.matrixTitle')}>
        {model.items.map((item) => (
          <article
            key={item.id}
            className={item.active ? 'sd-card sd-card-active' : 'sd-card'}
            role="listitem"
          >
            <div className="sd-head">
              <div>
                <p className="sd-title">{item.label}</p>
                <p className="sd-engine">{item.engine}</p>
              </div>
              <p className={item.tone ? `sd-signal sd-signal-${item.tone}` : 'sd-signal'}>
                {item.signal}
              </p>
            </div>

            <dl className="sd-meta">
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

            <p className="sd-source">{item.source}</p>
            {item.reason ? <p className="sd-reason">{item.reason}</p> : null}
          </article>
        ))}
      </div>
    </GlassPanel>
  )
}
