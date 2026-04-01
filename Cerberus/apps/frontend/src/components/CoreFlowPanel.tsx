import { useMemo } from 'react'

import { useI18n } from '../i18n/I18nProvider'
import { useDormantSelector } from '../store/useDormantSelector'
import type { CoreFlowStepState } from '../store/slices/shared'
import { buildCoreFlowPanelModel } from '../view-models/workbench'
import { GlassPanel, SectionFrame, StatusPill } from '../ui'

function toneClass(state: CoreFlowStepState): string {
  if (state === 'error') {
    return 'flow-card fc-error'
  }
  if (state === 'degraded') {
    return 'flow-card fc-warning'
  }
  if (state === 'success') {
    return 'flow-card fc-success'
  }
  return 'flow-card'
}

export function CoreFlowPanel({ active = true }: { active?: boolean }) {
  const { t } = useI18n()
  const flow = useDormantSelector(active, (state) => state.uiState.core_flow)
  const model = useMemo(() => buildCoreFlowPanelModel(flow, t), [flow, t])

  return (
    <SectionFrame
      title={t('flow.title')}
      description={model.summary}
      aside={<p className="panel-caption">{model.hint}</p>}
      className="core-flow-frame"
    >
      <div className="flow-grid" data-testid="core-flow-panel">
        {model.steps.map((step) => {
          return (
            <GlassPanel key={step.id} className={toneClass(step.state)} tone="subtle" data-testid={`core-flow-step-${step.id}`}>
              <div className="fc-head">
                <div>
                  <p className="fc-index">{step.indexLabel} {step.title}</p>
                  <p className="fc-updated">
                    {t('common.updatedAt')}: {step.updatedAt}
                  </p>
                </div>
                <StatusPill state={step.state} label={step.stateLabel} compact />
              </div>
              <p className="fc-reason">{step.reason}</p>
              {step.requestId ? <p className="fc-request">rid: {step.requestId}</p> : null}
            </GlassPanel>
          )
        })}
      </div>
    </SectionFrame>
  )
}
