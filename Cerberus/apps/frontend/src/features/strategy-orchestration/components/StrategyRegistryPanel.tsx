import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, EmptyState, GlassPanel } from '../../../ui'
import type { StrategyRegistryPanelModel } from '../view-models'

type Props = {
  model: StrategyRegistryPanelModel
}

export function StrategyRegistryPanel({ model }: Props) {
  const { t } = useI18n()

  if (model.rows.length === 0) {
    return (
      <GlassPanel className="strategy-registry-panel" tone="subtle">
        <EmptyState
          title={model.emptyTitle ?? model.summary}
          body={model.emptyHint ?? t('workspace.strategy.noDecisionsHint')}
        />
      </GlassPanel>
    )
  }

  return (
    <GlassPanel className="strategy-registry-panel" tone="subtle">
      <div className="strategy-panel-head">
        <div>
          <p className="subtle-label">{t('workspace.strategy.registryTitle')}</p>
          <p className="strategy-panel-summary">{model.summary}</p>
        </div>
        <div className="strategy-registry-policies">
          <p className="strategy-registry-policy">{model.policyLabel}</p>
          <p className="strategy-registry-downgrade">{model.downgradeLabel}</p>
        </div>
      </div>

      <div className="strategy-registry-list" role="list" aria-label={t('workspace.strategy.registryTitle')}>
        {model.rows.map((row) => (
          <article key={row.id} role="listitem" className="strategy-registry-row">
            <div className="strategy-registry-row-head">
              <div>
                <p className="subtle-label">{row.label}</p>
                <p className="strategy-registry-engine">{row.engine}</p>
              </div>
              <p
                className={
                  row.stateTone === 'accent'
                    ? 'strategy-registry-state strategy-registry-state-accent'
                    : row.stateTone === 'muted'
                      ? 'strategy-registry-state strategy-registry-state-muted'
                      : 'strategy-registry-state'
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
