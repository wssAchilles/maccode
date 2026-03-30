import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, GlassPanel } from '../../../ui'
import type { InferenceDiagnosticsModel } from '../view-models'

type Props = {
  model: InferenceDiagnosticsModel
}

export function InferenceSymbolComparisonPanel({ model }: Props) {
  const { t } = useI18n()

  return (
    <GlassPanel tone="subtle" className="inference-panel inference-panel-detail">
      <div className="inference-detail-head">
        <div>
          <p className="subtle-label">{t('workspace.inference.symbolComparison')}</p>
          <p className="inference-card-summary">{t('workspace.inference.comparisonSummary')}</p>
        </div>
      </div>

      {model.symbolComparisons.length > 0 ? (
        <div className="inference-symbol-list">
          {model.symbolComparisons.map((entry) => (
            <div key={entry.id} className="inference-symbol-row">
              <div>
                <p className="inference-symbol-title">{entry.symbol}</p>
                <p className="inference-symbol-meta">
                  {t('workspace.inference.comparedTicks')}: {entry.comparedTicks}
                </p>
              </div>
              <div className="inference-symbol-side">
                <p className={entry.tone === 'accent' ? 'inference-symbol-value inference-symbol-value-accent' : 'inference-symbol-value'}>
                  {entry.agreementRate}
                </p>
                <p className="inference-symbol-meta">
                  {t('workspace.inference.divergenceCount')}: {entry.divergenceCount}
                </p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-inline">{t('workspace.inference.noSymbolComparisons')}</div>
      )}

      {model.signalDistributions.length > 0 ? (
        <div className="inference-distribution-grid">
          {model.signalDistributions.map((group) => (
            <div key={group.id} className="inference-distribution-group">
              <p className="subtle-label">{group.label}</p>
              <DataList dense items={group.items} />
            </div>
          ))}
        </div>
      ) : null}
    </GlassPanel>
  )
}
