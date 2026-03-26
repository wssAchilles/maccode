import type { TranslationKey } from '../i18n/messages'
import { useI18n } from '../i18n/I18nProvider'
import { useCerberusStore } from '../store'
import type { CoreFlowStepId, CoreFlowStepState } from '../store/slices/shared'
import { GlassPanel, SectionFrame, StatusPill } from '../ui'

const STEP_ORDER: CoreFlowStepId[] = ['bootstrap', 'market', 'precheck', 'submit', 'feedback', 'cancel']

const STEP_LABEL_MAP: Record<CoreFlowStepId, TranslationKey> = {
  bootstrap: 'flow.step.bootstrap',
  market: 'flow.step.market',
  precheck: 'flow.step.precheck',
  submit: 'flow.step.submit',
  feedback: 'flow.step.feedback',
  cancel: 'flow.step.cancel',
}

const STATE_LABEL_MAP: Record<CoreFlowStepState, TranslationKey> = {
  idle: 'health.state.idle',
  active: 'health.state.loading',
  success: 'health.state.ready',
  degraded: 'health.state.degraded',
  error: 'health.state.error',
}

function toneClass(state: CoreFlowStepState): string {
  if (state === 'error') {
    return 'flow-card flow-card-error'
  }
  if (state === 'degraded') {
    return 'flow-card flow-card-warning'
  }
  if (state === 'success') {
    return 'flow-card flow-card-success'
  }
  return 'flow-card'
}

export function CoreFlowPanel() {
  const { t } = useI18n()
  const flow = useCerberusStore((state) => state.uiState.core_flow)

  return (
    <SectionFrame title={t('flow.title')} description={t('workspace.overview.description')} className="core-flow-frame">
      <div className="flow-grid" data-testid="core-flow-panel">
        {STEP_ORDER.map((step, index) => {
          const item = flow[step]
          return (
            <GlassPanel key={step} className={toneClass(item.state)} tone="subtle" data-testid={`core-flow-step-${step}`}>
              <div className="flow-card-head">
                <div>
                  <p className="flow-card-index">{index + 1}. {t(STEP_LABEL_MAP[step])}</p>
                  <p className="flow-card-updated">
                    {t('common.updatedAt')}: {item.last_update_ms ? new Date(item.last_update_ms).toLocaleTimeString() : t('common.na')}
                  </p>
                </div>
                <StatusPill state={item.state} label={t(STATE_LABEL_MAP[item.state])} compact />
              </div>
              <p className="flow-card-reason">{item.reason?.trim().length ? item.reason : t('common.na')}</p>
              {item.request_id ? <p className="flow-card-request">rid: {item.request_id}</p> : null}
            </GlassPanel>
          )
        })}
      </div>
    </SectionFrame>
  )
}
