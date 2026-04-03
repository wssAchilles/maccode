import { useMemo } from 'react'
import { useShallow } from 'zustand/react/shallow'

import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import { useDormantSelector } from '../../store/useDormantSelector'
import { buildPreparedTradingSnapshot } from '../../view-models/workbench'
import {
  buildStrategyContextBandModel,
  buildStrategyDecisionMatrixModel,
  buildStrategyOrchestrationAuditTimelineModel,
  buildStrategyPortfolioPanelModel,
  buildStrategyRegistryPanelModel,
} from '../strategy-orchestration/view-models'
import { useStrategyOrchestrationOperationsModel } from '../strategy-orchestration/useStrategyOrchestrationOperationsModel'

type Params = {
  active: boolean
}

export function useStrategyWorkspaceModel({ active }: Params) {
  const { t } = useI18n()
  const {
    selectedSymbol,
    latest,
    latestBySymbol,
    latestEvent,
    heartbeat,
    strategySignal,
    orchestrationStatus,
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
      orchestrationStatus: state.strategySummary.orchestration_status,
      summaryError: state.strategySummary.last_error,
    })),
  )
  const setSelectedSymbol = useCerberusStore((state) => state.marketStreamActions.setSelectedSymbol)
  const syncExecutionFilters = useCerberusStore((state) => state.executionTradingActions.setFilters)
  const operations = useStrategyOrchestrationOperationsModel(active)

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
    const portfolioPanel = buildStrategyPortfolioPanelModel({ t, signal: strategySignal, selectedSymbol })
    const strategyMatrix = buildStrategyDecisionMatrixModel({ t, signal: strategySignal })
    const strategyRegistry = buildStrategyRegistryPanelModel({
      t,
      signal: strategySignal,
      selectedSymbol,
      orchestrationStatus,
    })
    const strategyAuditTimeline = buildStrategyOrchestrationAuditTimelineModel({ t, orchestrationStatus })
    const contextBand = buildStrategyContextBandModel({ t, signal: strategySignal, selectedSymbol, orchestrationStatus })

    return {
      portfolioPanel,
      strategyMatrix,
      strategyRegistry,
      strategyAuditTimeline,
      contextBand,
      spotlight: {
        summary: strategyMatrix.summary,
        hint: contextBand.hint,
        chips: [tradingSnapshot.selectedSymbol, tradingSnapshot.signalValue],
        accent: 'teal' as const,
        postureLabel: t('workspace.strategy.title'),
        metrics: [
          {
            id: 'signal',
            label: t('strategy.signal'),
            value: tradingSnapshot.signalValue,
            tone: 'accent' as const,
            visualPriority: 'primary' as const,
          },
          {
            id: 'confidence',
            label: t('strategy.confidence'),
            value: tradingSnapshot.confidenceValue,
          },
          {
            id: 'lead',
            label: t('workspace.strategy.leadStrategy'),
            value: portfolioPanel.items[0]?.value ?? t('common.na'),
          },
          {
            id: 'gate',
            label: t('workspace.strategy.executionGate'),
            value: portfolioPanel.gateLabel,
            tone: portfolioPanel.gateTone === 'accent' ? 'accent' as const : 'default' as const,
          },
        ],
      },
      operatorSections: [
        {
          id: 'signal-posture',
          title: t('workspace.strategy.portfolioTitle'),
          summary: contextBand.title,
          accent: 'teal' as const,
          postureLabel: portfolioPanel.gateLabel,
          visualPriority: 'hero' as const,
          items: [
            {
              id: 'final-signal',
              label: t('workspace.strategy.finalSignal'),
              value: contextBand.items[1]?.value ?? t('common.na'),
              tone: contextBand.items[1]?.tone,
            },
            {
              id: 'execution-gate',
              label: t('workspace.strategy.executionGate'),
              value: contextBand.items[2]?.value ?? t('common.na'),
            },
            {
              id: 'consensus',
              label: t('workspace.strategy.consensusTitle'),
              value: contextBand.items[3]?.value ?? t('common.na'),
            },
            {
              id: 'updated-at',
              label: t('common.updatedAt'),
              value: contextBand.items[7]?.value ?? t('common.na'),
            },
          ],
        },
        {
          id: 'policy-posture',
          title: t('workspace.strategy.operationsTitle'),
          summary: strategyRegistry.band?.hint ?? strategyRegistry.summary,
          accent: 'cyan' as const,
          postureLabel: strategyRegistry.policyLabel,
          items:
            strategyRegistry.band?.items ?? [
              {
                id: 'empty',
                label: t('workspace.strategy.registryTitle'),
                value: strategyRegistry.emptyTitle ?? t('workspace.strategy.registryEmpty'),
              },
            ],
        },
      ],
    }
  }, [orchestrationStatus, selectedSymbol, strategySignal, t, tradingSnapshot])

  const selectSymbol = (symbol: string) => {
    setSelectedSymbol(symbol)
    syncExecutionFilters({ symbol })
  }

  return {
    selectedSymbol,
    selectSymbol,
    summaryError,
    operations,
    ...model,
  }
}
