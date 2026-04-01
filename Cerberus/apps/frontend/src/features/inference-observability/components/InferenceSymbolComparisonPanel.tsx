import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, GlassPanel } from '../../../ui'
import type { InferenceDiagnosticsModel } from '../view-models'

type Props = {
  model: InferenceDiagnosticsModel
}

export function InferenceSymbolComparisonPanel({ model }: Props) {
  const { t } = useI18n()

  return (
    <GlassPanel tone="subtle" className="ifp ip-detail">
      <div className="idt-head">
        <div>
          <p className="subtle-label">{t('workspace.inference.symbolComparison')}</p>
          <p className="ifc-summary">{t('workspace.inference.comparisonSummary')}</p>
        </div>
      </div>

      {model.symbolComparisons.length > 0 ? (
        <div className="isy-list">
          {model.symbolComparisons.map((entry) => (
            <div key={entry.id} className="isy-row">
              <div>
                <p className="isy-title">{entry.symbol}</p>
                <p className="isy-meta">
                  {t('workspace.inference.comparedTicks')}: {entry.comparedTicks}
                </p>
              </div>
              <div className="isy-side">
                <p className={entry.tone === 'accent' ? 'isy-value isy-value-accent' : 'isy-value'}>
                  {entry.agreementRate}
                </p>
                <p className="isy-meta">
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
        <div className="ids-grid">
          {model.signalDistributions.map((group) => (
            <div key={group.id} className="ids-group">
              <p className="subtle-label">{group.label}</p>
              <DataList dense items={group.items} />
            </div>
          ))}
        </div>
      ) : null}
    </GlassPanel>
  )
}
