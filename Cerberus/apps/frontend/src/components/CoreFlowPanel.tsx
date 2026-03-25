import type { TranslationKey } from '../i18n/messages'
import { useI18n } from '../i18n/I18nProvider'
import { useCerberusStore } from '../store'
import type { CoreFlowStepId, CoreFlowStepState } from '../store/slices/shared'

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

function stateClass(state: CoreFlowStepState): string {
  if (state === 'success') {
    return 'status-chip status-ready'
  }
  if (state === 'degraded') {
    return 'status-chip status-degraded'
  }
  if (state === 'error') {
    return 'status-chip status-error'
  }
  if (state === 'active') {
    return 'status-chip status-loading'
  }
  return 'status-chip'
}

function reasonClass(state: CoreFlowStepState): string {
  if (state === 'error') {
    return 'text-rose-200'
  }
  if (state === 'degraded') {
    return 'text-amber-200'
  }
  if (state === 'success') {
    return 'text-emerald-200'
  }
  return 'text-slate-400'
}

export function CoreFlowPanel() {
  const { t } = useI18n()
  const flow = useCerberusStore((state) => state.uiState.core_flow)

  return (
    <article className="panel-card" data-testid="core-flow-panel" aria-label={t('flow.title')}>
      <h3 className="panel-title">{t('flow.title')}</h3>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {STEP_ORDER.map((step, index) => {
          const item = flow[step]
          return (
            <div
              key={step}
              className="rounded-xl border border-slate-700/70 bg-slate-950/45 p-3"
              data-testid={`core-flow-step-${step}`}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold text-cyan-200">
                  {index + 1}. {t(STEP_LABEL_MAP[step])}
                </p>
                <span className={stateClass(item.state)}>{t(STATE_LABEL_MAP[item.state])}</span>
              </div>
              <p className={`mt-2 text-[11px] ${reasonClass(item.state)}`}>
                {item.reason?.trim().length ? item.reason : t('common.na')}
              </p>
              <p className="mt-1 text-[11px] text-slate-500">
                {t('common.updatedAt')}:{' '}
                {item.last_update_ms ? new Date(item.last_update_ms).toLocaleTimeString() : t('common.na')}
              </p>
              {item.request_id ? (
                <p className="mt-1 truncate text-[11px] text-slate-500">rid: {item.request_id}</p>
              ) : null}
            </div>
          )
        })}
      </div>
    </article>
  )
}
