import { useI18n } from '../../i18n/I18nProvider'
import { useCerberusStore } from '../../store'
import type { WorkspaceId } from '../../store/slices/shared'
import { buildHealthCards, formatConfidence, formatPrice, summarizeLatestEventAt, summarizeLatestFeedback } from '../../view-models/workbench'
import { DataList, GlassPanel, InlineAlert, MetricTile, SectionFrame, StatusPill } from '../../ui'
import { CoreFlowPanel } from '../../components/CoreFlowPanel'

type Props = {
  active?: boolean
  onSelectWorkspace: (workspace: WorkspaceId) => void
}

export function OverviewWorkspace({ active: _active = true, onSelectWorkspace }: Props) {
  const { t } = useI18n()
  const selectedSymbol = useCerberusStore((state) => state.marketStream.selected_symbol)
  const latest = useCerberusStore((state) => state.marketStream.latest)
  const latestBySymbol = useCerberusStore((state) => state.marketStream.latest_by_symbol)
  const strategySignal = useCerberusStore((state) => state.strategySummary.signal)
  const recentSignals = useCerberusStore((state) => state.strategySummary.recent_signals)
  const persistenceStatus = useCerberusStore((state) => state.strategySummary.persistence_status)
  const summaryError = useCerberusStore((state) => state.strategySummary.last_error)
  const latestEvent = useCerberusStore((state) => state.executionTrading.latest_event)
  const heartbeat = useCerberusStore((state) => state.executionTrading.heartbeat)
  const domainStatus = useCerberusStore((state) => state.uiState.domain_status)

  const displayQuote = latestBySymbol[selectedSymbol] ?? latest
  const healthCards = buildHealthCards(domainStatus, t)

  return (
    <div className="workspace-grid">
      <SectionFrame
        title={t('workspace.overview.title')}
        description={t('workspace.overview.description')}
        eyebrow={t('workspace.overview.eyebrow')}
        aside={
          <div className="workspace-actions">
            <button type="button" className="soft-button soft-button-primary" onClick={() => onSelectWorkspace('execution')}>
              {t('workspace.cta.execution')}
            </button>
            <button type="button" className="soft-button" onClick={() => onSelectWorkspace('health')}>
              {t('workspace.cta.health')}
            </button>
          </div>
        }
        className="workspace-span-full"
        tone="hero"
      >
        <div className="metric-grid">
          <MetricTile label={t('market.bestBid')} value={formatPrice(displayQuote?.bid_price)} tone="positive" hint={selectedSymbol} />
          <MetricTile label={t('market.bestAsk')} value={formatPrice(displayQuote?.ask_price)} tone="negative" hint={selectedSymbol} />
          <MetricTile
            label={t('strategy.signal')}
            value={strategySignal?.signal ?? 'HOLD'}
            tone="accent"
            hint={`${t('strategy.confidence')}: ${formatConfidence(strategySignal?.confidence)}`}
          />
          <MetricTile
            label={t('workspace.overview.feedback')}
            value={summarizeLatestFeedback(latestEvent, heartbeat, t)}
            hint={summarizeLatestEventAt(latestEvent)}
          />
        </div>
      </SectionFrame>

      {summaryError ? (
        <InlineAlert title={t('workspace.overview.attention')} tone="warning" className="workspace-span-full">
          {summaryError.message}
        </InlineAlert>
      ) : null}

      <div className="workspace-main">
        <CoreFlowPanel />
      </div>

      <div className="workspace-side stack">
        <SectionFrame title={t('workspace.overview.healthDigest')} description={t('workspace.health.description')}>
          <div className="stack-sm">
            {healthCards.map((card) => (
              <GlassPanel key={card.id} className="health-digest-card" tone="subtle">
                <div className="health-digest-head">
                  <div>
                    <p className="subtle-label">{card.title}</p>
                    <p className="health-digest-meta">{card.staleLabel}</p>
                  </div>
                  <StatusPill state={card.state} label={card.stateLabel} compact />
                </div>
                <p className="health-digest-updated">{t('common.updatedAt')}: {card.updatedAt}</p>
                {card.reason ? <p className="health-digest-reason">{card.reason}</p> : null}
              </GlassPanel>
            ))}
          </div>
        </SectionFrame>

        <SectionFrame title={t('strategy.recent')} description={t('workspace.overview.signalsDescription')}>
          {recentSignals.length === 0 ? (
            <p className="empty-inline">{t('strategy.noData')}</p>
          ) : (
            <div className="stack-sm">
              {recentSignals.slice(0, 4).map((signal) => (
                <GlassPanel key={`${signal.created_at}-${signal.strategy_id}`} className="signal-card" tone="subtle">
                  <div className="signal-card-head">
                    <p className="signal-card-title">{signal.signal}</p>
                    <p className="signal-card-symbol">{signal.symbol}</p>
                  </div>
                  <DataList
                    dense
                    items={[
                      { id: 'confidence', label: t('strategy.confidence'), value: formatConfidence(signal.confidence) },
                      { id: 'createdAt', label: t('common.updatedAt'), value: new Date(signal.created_at).toLocaleString() },
                    ]}
                  />
                </GlassPanel>
              ))}
            </div>
          )}
          <div className="workspace-actions">
            <button type="button" className="soft-button" onClick={() => onSelectWorkspace('market')}>
              {t('workspace.cta.market')}
            </button>
            <button type="button" className="soft-button" onClick={() => onSelectWorkspace('execution')}>
              {t('workspace.cta.execution')}
            </button>
          </div>
        </SectionFrame>

        <SectionFrame title={t('strategy.persistence')} description={t('workspace.health.persistenceDescription')}>
          <DataList
            items={[
              {
                id: 'worker',
                label: t('strategy.ticksProcessed'),
                value: String(persistenceStatus?.worker.processed_ticks ?? 0),
              },
              {
                id: 'supabase',
                label: 'Supabase',
                value: String(persistenceStatus?.stores.supabase_enabled ?? false),
              },
              {
                id: 'firebase',
                label: 'Firestore',
                value: String(persistenceStatus?.stores.firebase_enabled ?? false),
              },
            ]}
          />
        </SectionFrame>
      </div>
    </div>
  )
}
