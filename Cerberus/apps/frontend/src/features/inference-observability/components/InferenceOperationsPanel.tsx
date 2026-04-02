import { DataList, InlineAlert, PanelSection, StatusPill, TerminalBand } from '../../../ui'
import { useI18n } from '../../../i18n/I18nProvider'
import type { InferenceOperationsModel } from '../view-models'

type Props = {
  model: InferenceOperationsModel
  reason: string
  selectedModelId: string
  onReasonChange: (value: string) => void
  onSelectedModelIdChange: (value: string) => void
  onPromote: () => void
  onRollback: () => void
  onActivate: () => void
}

export function InferenceOperationsPanel({
  model,
  reason,
  selectedModelId,
  onReasonChange,
  onSelectedModelIdChange,
  onPromote,
  onRollback,
  onActivate,
}: Props) {
  const { t } = useI18n()

  return (
    <div className="stack">
      <TerminalBand model={model.band} className="iop-band" compact />
      <div className="health-grid">
        <PanelSection
          className="ifp iop-panel"
          eyebrow={t('workspace.inference.operationsTitle')}
          title={model.summary}
          hint={t('workspace.inference.operationStatus')}
          aside={<StatusPill state={model.state} label={model.stateLabel} compact />}
        >
          <DataList
            items={[
              {
                id: 'targetMode',
                label: t('workspace.inference.targetMode'),
                value: model.targetModeLabel,
              },
              {
                id: 'effectiveMode',
                label: t('workspace.inference.rolloutMode'),
                value: model.effectiveModeLabel,
              },
              {
                id: 'gateBlockers',
                label: t('workspace.inference.gateBlockers'),
                value:
                  model.blockers.length > 0
                    ? model.blockers.join(' · ')
                    : t('workspace.inference.noGateBlockers'),
              },
            ]}
          />
        </PanelSection>

        <PanelSection
          className="ifp iop-panel"
          eyebrow={t('workspace.inference.operatorNote')}
          title={t('workspace.inference.operationStatus')}
          hint={t('workspace.inference.operatorNote')}
        >
          <div className="iop-form">
            <label className="field-label">
              {t('workspace.inference.operationReason')}
              <textarea
                id="inference-operation-reason"
                name="inference_operation_reason"
                className="field-input ifr"
                value={reason}
                onChange={(event) => onReasonChange(event.target.value)}
                rows={3}
              />
            </label>
            {model.modelOptions.length > 1 ? (
              <label className="field-label">
                {t('workspace.inference.registryTitle')}
                <select
                  id="inference-model-select"
                  name="inference_model_select"
                  className="field-input"
                  value={selectedModelId}
                  onChange={(event) => onSelectedModelIdChange(event.target.value)}
                >
                  {model.modelOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.active ? `${option.label} · ${t('common.ready')}` : option.label}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>
          <div className="ws-actions iop-actions">
            <button
              type="button"
              className="soft-button sbp"
              disabled={!model.canPromote}
              onClick={onPromote}
            >
              {model.pendingAction === 'promote'
                ? t('workspace.inference.actionPromoting')
                : t('workspace.inference.actionPromote')}
            </button>
            <button
              type="button"
              className="soft-button"
              disabled={!model.canRollback}
              onClick={onRollback}
            >
              {model.pendingAction === 'rollback'
                ? t('workspace.inference.actionRollingBack')
                : t('workspace.inference.actionRollback')}
            </button>
            {model.modelOptions.length > 1 ? (
              <button
                type="button"
                className="soft-button"
                disabled={!model.canActivateModel}
                onClick={onActivate}
              >
                {model.pendingAction === 'activate_model'
                  ? t('workspace.inference.actionActivatingModel')
                  : t('workspace.inference.actionActivateModel')}
              </button>
            ) : null}
          </div>
          {model.statusMessage ? (
            <InlineAlert
              title={t('workspace.inference.operationStatus')}
              tone={model.statusTone === 'danger' ? 'danger' : 'info'}
              className="iopn-alert"
            >
              {model.statusMessage}
            </InlineAlert>
          ) : null}
        </PanelSection>
      </div>
    </div>
  )
}
