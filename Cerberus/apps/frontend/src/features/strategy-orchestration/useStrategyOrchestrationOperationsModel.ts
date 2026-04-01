import { startTransition, useEffect, useMemo, useState } from 'react'

import { formatAppError } from '../../lib/http'
import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import { useDormantSelector } from '../../store/useDormantSelector'
import { buildStrategyOrchestrationOperationsModel } from './view-models'

type EntryDraft = {
  enabled: boolean
  priority: string
  observeWeight: string
  primaryWeight: string
  symbolCoverage: string
  conflictTargets: string
  downgradeAction: string
}

function coverageToDraft(value: string[]): string {
  return value.join(', ')
}

export function useStrategyOrchestrationOperationsModel(enabled = true) {
  const { t } = useI18n()
  const orchestrationStatus = useDormantSelector(enabled, (state) => state.strategySummary.orchestration_status)
  const lastResult = useDormantSelector(enabled, (state) => state.strategySummary.orchestration_last_result)
  const pendingAction = useDormantSelector(enabled, (state) => state.strategySummary.orchestration_pending_action)
  const lastError = useDormantSelector(enabled, (state) => state.strategySummary.last_error)
  const loadStrategyOrchestration = useCerberusStore((state) => state.strategySummaryActions.loadStrategyOrchestration)
  const updateEntry = useCerberusStore((state) => state.strategySummaryActions.updateStrategyOrchestrationEntry)
  const updatePolicies = useCerberusStore((state) => state.strategySummaryActions.updateStrategyOrchestrationPolicies)

  const [reason, setReason] = useState('')
  const [drafts, setDrafts] = useState<Record<string, EntryDraft>>({})
  const [conflictPolicy, setConflictPolicy] = useState('')
  const [downgradePolicy, setDowngradePolicy] = useState('')

  useEffect(() => {
    if (!enabled) {
      return
    }
    if (!orchestrationStatus) {
      void loadStrategyOrchestration()
    }
  }, [enabled, loadStrategyOrchestration, orchestrationStatus])

  useEffect(() => {
    if (!enabled || !orchestrationStatus) {
      return
    }
    startTransition(() => {
      setConflictPolicy(orchestrationStatus.conflict_policy)
      setDowngradePolicy(orchestrationStatus.downgrade_policy)
      setDrafts(
        Object.fromEntries(
          orchestrationStatus.entries.map((entry) => [
            entry.strategy_id,
            {
              enabled: entry.enabled,
              priority: String(entry.priority),
              observeWeight: String(entry.observe_weight),
              primaryWeight: String(entry.primary_weight),
              symbolCoverage: coverageToDraft(entry.symbol_coverage),
              conflictTargets: coverageToDraft(entry.conflict_targets),
              downgradeAction: entry.downgrade_action,
            },
          ]),
        ),
      )
    })
  }, [enabled, orchestrationStatus])

  const baseModel = useMemo(
    () =>
      buildStrategyOrchestrationOperationsModel({
        t,
        orchestrationStatus,
        lastResult,
      }),
    [lastResult, orchestrationStatus, t],
  )

  const model = useMemo(
    () => ({
      ...baseModel,
      pendingAction: pendingAction ?? undefined,
      statusMessage: baseModel.statusMessage ?? (lastError ? formatAppError(lastError) : undefined),
      statusTone: baseModel.statusTone ?? (lastError ? 'danger' : undefined),
    }),
    [baseModel, lastError, pendingAction],
  )

  return {
    model,
    reason,
    setReason,
    drafts,
    conflictPolicy,
    downgradePolicy,
    setConflictPolicy,
    setDowngradePolicy,
    setDraftField: (strategyId: string, field: keyof EntryDraft, value: string | boolean) => {
      setDrafts((current) => ({
        ...current,
        [strategyId]: {
          ...(current[strategyId] ?? {
            enabled: true,
            priority: '1',
            observeWeight: '0.5',
            primaryWeight: '0.5',
            symbolCoverage: '',
            conflictTargets: '',
            downgradeAction: 'review',
          }),
          [field]: value,
        },
      }))
    },
    onSaveEntry: async (strategyId: string) => {
      const draft = drafts[strategyId]
      if (!draft) {
        return
      }
      await updateEntry(
        strategyId,
        {
          enabled: draft.enabled,
          priority: Number.parseInt(draft.priority, 10),
          observe_weight: Number.parseFloat(draft.observeWeight),
          primary_weight: Number.parseFloat(draft.primaryWeight),
          symbol_coverage: draft.symbolCoverage
            .split(',')
            .map((item) => item.trim().toUpperCase())
            .filter(Boolean),
          conflict_targets: draft.conflictTargets
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean),
          downgrade_action: draft.downgradeAction || undefined,
        },
        reason,
      )
    },
    onSavePolicies: async () => {
      await updatePolicies(
        {
          conflict_policy: conflictPolicy || undefined,
          downgrade_policy: downgradePolicy || undefined,
        },
        reason,
      )
    },
  }
}
