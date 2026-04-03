import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, EmptyState, GlassPanel, PanelSection, TerminalBand } from '../../../ui'
import type { StrategyRegistryPanelModel } from '../view-models'

type Props = {
  model: StrategyRegistryPanelModel
}

export function StrategyRegistryPanel({ model }: Props) {
  const { t } = useI18n()

  if (model.rows.length === 0) {
    return (
      <GlassPanel className="srg-panel" tone="subtle">
        {model.band ? <TerminalBand model={model.band} className="sp-band" compact hideHint hideEyebrow /> : null}
        <EmptyState
          title={model.emptyTitle ?? model.summary}
          body={model.emptyHint ?? t('workspace.strategy.noDecisionsHint')}
        />
      </GlassPanel>
    )
  }

  return (
    <GlassPanel className="srg-panel" tone="subtle">
      {model.band ? <TerminalBand model={model.band} className="sp-band" compact hideHint hideEyebrow /> : null}
      <PanelSection
        className="srg-summary-section"
        eyebrow={t('workspace.strategy.registryTitle')}
        title={model.summary}
        hint={model.stateSummary ?? t('workspace.strategy.registryDescription')}
        compact
        aside={
          <div className="srg-policies">
            <p className="srg-policy">{model.policyLabel}</p>
            <p className="srg-downgrade">{model.downgradeLabel}</p>
          </div>
        }
      />

      <div className="srg-list" role="list" aria-label={t('workspace.strategy.registryTitle')}>
        {model.rows.map((row) => (
          <PanelSection
            key={row.id}
            className="srg-row"
            eyebrow={row.engine}
            title={row.label}
            hint={row.detailHint}
            compact
            aside={
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
            }
          >
            {row.impactLabel ? <p className="srg-impact">{row.impactLabel}</p> : null}
            <DataList items={row.items} />
          </PanelSection>
        ))}
      </div>
    </GlassPanel>
  )
}
