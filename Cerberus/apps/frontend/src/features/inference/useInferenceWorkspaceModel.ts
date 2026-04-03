import { useMemo } from 'react'
import { useShallow } from 'zustand/react/shallow'

import { useI18n } from '../../i18n/I18nProvider'
import { useDormantSelector } from '../../store/useDormantSelector'
import { buildPreparedTradingSnapshot } from '../../view-models/workbench'
import { useInferenceOperationsModel } from '../inference-observability/useInferenceOperationsModel'
import {
  buildInferenceDiagnosticsModel,
  buildInferenceStatusCardModel,
} from '../inference-observability/view-models'

type Params = {
  active: boolean
}

export function useInferenceWorkspaceModel({ active }: Params) {
  const { t } = useI18n()
  const {
    selectedSymbol,
    latest,
    latestBySymbol,
    latestEvent,
    heartbeat,
    strategySignal,
    inferenceStatus,
    summaryError,
  } = useDormantSelector(
    active,
    useShallow((state) => ({
      selectedSymbol: state.marketStream.selected_symbol,
      latest: state.marketStream.latest,
      latestBySymbol: state.marketStream.latest_by_symbol,
      latestEvent: state.executionTrading.latest_event,
      heartbeat: state.executionTrading.heartbeat,
      strategySignal: state.strategySummary.signal,
      inferenceStatus: state.strategySummary.inference_status,
      summaryError: state.strategySummary.last_error,
    })),
  )
  const operations = useInferenceOperationsModel(active)

  const tradingSnapshot = useMemo(
    () =>
      buildPreparedTradingSnapshot({
        selectedSymbol,
        latest,
        latestBySymbol,
        strategySignal,
        latestEvent,
        heartbeat,
      }),
    [heartbeat, latest, latestBySymbol, latestEvent, selectedSymbol, strategySignal],
  )

  const model = useMemo(() => {
    const inferenceCard = buildInferenceStatusCardModel({ t, inferenceStatus })
    const diagnostics = buildInferenceDiagnosticsModel({ t, inferenceStatus })

    return {
      inferenceCard,
      diagnostics,
      spotlight: {
        summary: inferenceCard.summary,
        hint: inferenceCard.reason ?? diagnostics.band.hint,
        chips: [tradingSnapshot.selectedSymbol, tradingSnapshot.signalValue],
        accent: inferenceCard.reason ? 'amber' as const : 'teal' as const,
        postureLabel: t('workspace.inference.title'),
        metrics: [
          {
            id: 'runtime',
            label: t('workspace.inference.runtimeStatus'),
            value: inferenceCard.stateLabel,
            tone: inferenceCard.reason ? 'negative' as const : 'accent' as const,
            visualPriority: 'primary' as const,
          },
          {
            id: 'model',
            label: t('workspace.inference.model'),
            value: diagnostics.modelItems[0]?.value ?? t('workspace.inference.noModel'),
          },
          {
            id: 'observed',
            label: t('workspace.inference.observedTicks'),
            value: diagnostics.comparisonItems[0]?.value ?? t('common.na'),
          },
          {
            id: 'agreement',
            label: t('workspace.inference.agreementRate'),
            value: diagnostics.comparisonItems[2]?.value ?? t('common.na'),
          },
        ],
      },
      operatorSections: [
        {
          id: 'runtime',
          title: t('workspace.inference.runtimeStatus'),
          summary: inferenceCard.summary,
          accent: inferenceCard.reason ? 'amber' as const : 'teal' as const,
          postureLabel: inferenceCard.stateLabel,
          visualPriority: 'hero' as const,
          items: inferenceCard.items.slice(0, 4),
        },
        {
          id: 'operations',
          title: t('workspace.inference.operationsTitle'),
          summary: operations.model.band.hint,
          accent: operations.model.blockers.length > 0 ? 'amber' as const : 'cyan' as const,
          postureLabel: operations.model.targetModeLabel,
          items: operations.model.band.items,
        },
      ],
    }
  }, [
    inferenceStatus,
    operations.model.band.hint,
    operations.model.band.items,
    operations.model.blockers.length,
    operations.model.targetModeLabel,
    t,
    tradingSnapshot,
  ])

  return {
    summaryError,
    operations,
    ...model,
  }
}
