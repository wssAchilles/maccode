import { useI18n } from '../../../i18n/I18nProvider'
import { DataList, PanelSection, TerminalBand } from '../../../ui'
import type { InferenceDiagnosticsModel } from '../view-models'

type Props = {
  model: InferenceDiagnosticsModel
}

export function InferenceSymbolComparisonPanel({ model }: Props) {
  const { t } = useI18n()

  return (
    <div className="stack ip-detail">
      <TerminalBand model={model.symbolBand} className="if-sub-band" compact hideHint hideEyebrow />
      <PanelSection
        className="ifp ip-detail-section"
        eyebrow={t('workspace.inference.symbolComparison')}
        title={model.symbolBand.title}
        hideEyebrow
        compact
      >
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
              <PanelSection
                key={group.id}
                className="ids-group"
                title={group.label}
                hideEyebrow
                compact
              >
                <DataList dense items={group.items} />
              </PanelSection>
            ))}
          </div>
        ) : null}
      </PanelSection>
    </div>
  )
}
