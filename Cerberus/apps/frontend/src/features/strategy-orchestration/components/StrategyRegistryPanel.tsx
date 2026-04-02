import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, EmptyState, GlassPanel, TerminalBand } from '../../../ui'
import type { StrategyRegistryPanelModel } from '../view-models'

type Props = {
  model: StrategyRegistryPanelModel
}

export function StrategyRegistryPanel({ model }: Props) {
  const { t } = useI18n()

  if (model.rows.length === 0) {
    return (
      <GlassPanel className="srg-panel" tone="subtle">
        <EmptyState
          title={model.emptyTitle ?? model.summary}
          body={model.emptyHint ?? t('workspace.strategy.noDecisionsHint')}
        />
      </GlassPanel>
    )
  }

  return (
    <GlassPanel className="srg-panel" tone="subtle">
      <div className="sp-head">
        <div>
          <p className="subtle-label">{t('workspace.strategy.registryTitle')}</p>
          <p className="sp-summary">{model.summary}</p>
          {model.stateSummary ? <p className="sp-hint">{model.stateSummary}</p> : null}
        </div>
        <div className="srg-policies">
          <p className="srg-policy">{model.policyLabel}</p>
          <p className="srg-downgrade">{model.downgradeLabel}</p>
        </div>
      </div>
      {model.band ? <TerminalBand model={model.band} className="sp-band" /> : null}

      <div className="srg-list" role="list" aria-label={t('workspace.strategy.registryTitle')}>
        {model.rows.map((row) => (
          <article key={row.id} role="listitem" className="srg-row">
            <div className="srg-row-head">
              <div>
                <p className="subtle-label">{row.label}</p>
                <p className="srg-engine">{row.engine}</p>
                {row.impactLabel ? <p className="srg-impact">{row.impactLabel}</p> : null}
                {row.detailHint ? <p className="sp-hint">{row.detailHint}</p> : null}
              </div>
              <p
                className={
                  row.stateTone === 'accent'
                    ? 'srg-state srg-state-accent'
                    : row.stateTone === 'muted'
                      ? 'srg-state srg-state-muted'
                      : 'srg-state'
                }
              >
                {row.stateLabel}
              </p>
            </div>
            <DataList items={row.items} />
          </article>
        ))}
      </div>
    </GlassPanel>
  )
}
