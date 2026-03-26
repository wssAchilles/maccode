import { ExecutionConsole } from '../../components/ExecutionConsole'
import { ExecutionTimelinePanel } from '../../components/ExecutionTimelinePanel'
import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import { formatConfidence, summarizeLatestFeedback, summarizeLatestEventAt } from '../../view-models/workbench'
import { DiagnosticDrawer, MetricTile, SectionFrame } from '../../ui'

type Props = {
  active?: boolean
}

export function ExecutionWorkspace({ active = true }: Props) {
  const { t } = useI18n()
  const selectedSymbol = useCerberusStore((state) => state.marketStream.selected_symbol)
  const latest = useCerberusStore((state) => state.marketStream.latest)
  const latestBySymbol = useCerberusStore((state) => state.marketStream.latest_by_symbol)
  const strategySignal = useCerberusStore((state) => state.strategySummary.signal)
  const latestEvent = useCerberusStore((state) => state.executionTrading.latest_event)
  const heartbeat = useCerberusStore((state) => state.executionTrading.heartbeat)
  const summaryError = useCerberusStore((state) => state.strategySummary.last_error)

  const displayQuote = latestBySymbol[selectedSymbol] ?? latest

  return (
    <div className="workspace-grid">
      <SectionFrame
        title={t('workspace.execution.title')}
        description={t('workspace.execution.description')}
        eyebrow={t('workspace.execution.eyebrow')}
        className="workspace-span-full"
      >
        <div className="metric-grid">
          <MetricTile label={t('strategy.signal')} value={strategySignal?.signal ?? 'HOLD'} hint={`${t('strategy.confidence')}: ${formatConfidence(strategySignal?.confidence)}`} tone="accent" />
          <MetricTile label={t('market.bestBid')} value={displayQuote?.bid_price ?? '—'} tone="positive" />
          <MetricTile label={t('market.bestAsk')} value={displayQuote?.ask_price ?? '—'} tone="negative" />
          <MetricTile label={t('execution.timeline')} value={summarizeLatestFeedback(latestEvent, heartbeat, t)} hint={summarizeLatestEventAt(latestEvent)} />
        </div>
      </SectionFrame>

      <div className="workspace-main stack">
        <SectionFrame title={t('workspace.execution.ticketTitle')} description={t('workspace.execution.ticketDescription')}>
          <ExecutionConsole
            active={active}
            selectedSymbol={selectedSymbol}
            latestBid={displayQuote?.bid_price}
            latestAsk={displayQuote?.ask_price}
          />
        </SectionFrame>
      </div>

      <div className="workspace-side stack">
        {summaryError ? (
          <DiagnosticDrawer title={t('workspace.execution.diagnostics')} summary={summaryError.message}>
            <pre className="diagnostic-pre">{JSON.stringify(summaryError, null, 2)}</pre>
          </DiagnosticDrawer>
        ) : null}
        <SectionFrame title={t('execution.timeline')} description={t('workspace.execution.timelineDescription')}>
          <ExecutionTimelinePanel active={active} />
        </SectionFrame>
      </div>
    </div>
  )
}
