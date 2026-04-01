import { useI18n } from '../../../i18n/I18nProvider'
import { EmptyState, GlassPanel, InlineAlert } from '../../../ui'
import type { StrategyOrchestrationOperationsModel } from '../view-models'

type EntryDraft = {
  enabled: boolean
  priority: string
  observeWeight: string
  primaryWeight: string
  symbolCoverage: string
}

type Props = {
  model: StrategyOrchestrationOperationsModel
  drafts: Record<string, EntryDraft>
  reason: string
  conflictPolicy: string
  downgradePolicy: string
  onReasonChange: (value: string) => void
  onConflictPolicyChange: (value: string) => void
  onDowngradePolicyChange: (value: string) => void
  onDraftFieldChange: (strategyId: string, field: keyof EntryDraft, value: string | boolean) => void
  onSaveEntry: (strategyId: string) => void
  onSavePolicies: () => void
}

export function StrategyOrchestrationOperationsPanel({
  model,
  drafts,
  reason,
  conflictPolicy,
  downgradePolicy,
  onReasonChange,
  onConflictPolicyChange,
  onDowngradePolicyChange,
  onDraftFieldChange,
  onSaveEntry,
  onSavePolicies,
}: Props) {
  const { t } = useI18n()

  if (model.rows.length === 0) {
    return (
      <GlassPanel className="strategy-orchestration-operations-panel" tone="subtle">
        <EmptyState
          title={model.emptyTitle ?? model.summary}
          body={model.emptyHint ?? t('workspace.strategy.noDecisionsHint')}
        />
      </GlassPanel>
    )
  }

  const policyPending = model.pendingAction === 'update_policies'

  return (
    <GlassPanel className="strategy-orchestration-operations-panel" tone="subtle">
      <div className="strategy-panel-head">
        <div>
          <p className="subtle-label">{t('workspace.strategy.operationsTitle')}</p>
          <p className="strategy-panel-summary">{model.summary}</p>
          <p className="strategy-panel-hint">{model.policySummary}</p>
        </div>
      </div>

      <div className="strategy-orchestration-policy-grid">
        <label className="field-label">
          {t('workspace.strategy.conflictPolicy')}
          <select
            className="field-input"
            value={conflictPolicy}
            onChange={(event) => onConflictPolicyChange(event.target.value)}
          >
            {model.conflictOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field-label">
          {t('workspace.strategy.downgradePolicy')}
          <select
            className="field-input"
            value={downgradePolicy}
            onChange={(event) => onDowngradePolicyChange(event.target.value)}
          >
            {model.downgradeOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="field-label">
        {t('workspace.strategy.operatorNote')}
        <textarea
          className="field-input inference-reason-input"
          rows={3}
          value={reason}
          onChange={(event) => onReasonChange(event.target.value)}
        />
      </label>

      <div className="strategy-orchestration-row-list" role="list" aria-label={t('workspace.strategy.operationsTitle')}>
        {model.rows.map((row) => {
          const draft = drafts[row.id]
          const entryPending = model.pendingAction === `update_entry:${row.id}`
          return (
            <article key={row.id} className="strategy-orchestration-row" role="listitem">
              <div className="strategy-orchestration-row-head">
                <div>
                  <p className="subtle-label">{row.label}</p>
                  <p className="strategy-registry-engine">{row.engine}</p>
                  <p className="strategy-panel-hint">
                    {row.sourceLabel} · {row.roleLabel}
                  </p>
                </div>
                <label className="toggle-chip">
                  <input
                    type="checkbox"
                    checked={draft?.enabled ?? false}
                    onChange={(event) => onDraftFieldChange(row.id, 'enabled', event.target.checked)}
                  />
                  <span>{draft?.enabled ? t('common.ready') : t('common.disabled')}</span>
                </label>
              </div>

              <div className="strategy-orchestration-editor-grid">
                <label className="field-label">
                  {t('workspace.strategy.priority')}
                  <input
                    className="field-input"
                    type="number"
                    min="1"
                    max="100"
                    value={draft?.priority ?? '1'}
                    onChange={(event) => onDraftFieldChange(row.id, 'priority', event.target.value)}
                  />
                </label>
                <label className="field-label">
                  {t('workspace.strategy.observeWeight')}
                  <input
                    className="field-input"
                    type="number"
                    min="0"
                    step="0.05"
                    value={draft?.observeWeight ?? '0'}
                    onChange={(event) => onDraftFieldChange(row.id, 'observeWeight', event.target.value)}
                  />
                </label>
                <label className="field-label">
                  {t('workspace.strategy.primaryWeight')}
                  <input
                    className="field-input"
                    type="number"
                    min="0"
                    step="0.05"
                    value={draft?.primaryWeight ?? '0'}
                    onChange={(event) => onDraftFieldChange(row.id, 'primaryWeight', event.target.value)}
                  />
                </label>
                <label className="field-label strategy-orchestration-coverage-field">
                  {t('workspace.strategy.symbolCoverage')}
                  <input
                    className="field-input"
                    value={draft?.symbolCoverage ?? ''}
                    onChange={(event) => onDraftFieldChange(row.id, 'symbolCoverage', event.target.value)}
                    placeholder="BTCUSDT, ETHUSDT"
                  />
                </label>
              </div>

              <div className="strategy-orchestration-row-meta">
                <p>{t('workspace.strategy.runtimeState')}: {row.stateLabel}</p>
                <p>{t('workspace.strategy.conflictTargets')}: {row.conflictTargetsLabel}</p>
                <p>{t('workspace.strategy.symbolCoverage')}: {row.coverageLabel}</p>
              </div>

              <div className="workspace-actions strategy-orchestration-actions">
                <button
                  type="button"
                  className="soft-button soft-button-primary"
                  disabled={Boolean(model.pendingAction)}
                  onClick={() => onSaveEntry(row.id)}
                >
                  {entryPending ? t('workspace.strategy.actionSavingRow') : t('workspace.strategy.actionSaveRow')}
                </button>
              </div>
            </article>
          )
        })}
      </div>

      <div className="workspace-actions strategy-orchestration-actions">
        <button
          type="button"
          className="soft-button"
          disabled={Boolean(model.pendingAction)}
          onClick={onSavePolicies}
        >
          {policyPending ? t('workspace.strategy.actionSavingPolicies') : t('workspace.strategy.actionSavePolicies')}
        </button>
      </div>

      {model.statusMessage ? (
        <InlineAlert
          title={t('workspace.strategy.operationStatus')}
          tone={model.statusTone === 'danger' ? 'danger' : 'info'}
        >
          {model.statusMessage}
        </InlineAlert>
      ) : null}
    </GlassPanel>
  )
}
