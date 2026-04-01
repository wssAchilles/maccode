import type { MatchingOrderBookLevelRowModel, MatchingOrderBookPanelModel } from '../view-models/orderbook'
import { EmptyState, GlassPanel, SectionFrame } from '../ui'

type Props = {
  model: MatchingOrderBookPanelModel
}

function LevelGroup({
  title,
  levels,
  tone,
  emptyTitle,
  emptyBody,
}: {
  title: string
  levels: MatchingOrderBookLevelRowModel[]
  tone: 'bid' | 'ask'
  emptyTitle: string
  emptyBody: string
}) {
  return (
    <div className="obg">
      <p className="subtle-label">{title}</p>
      {levels.length === 0 ? (
        <EmptyState title={emptyTitle} body={emptyBody} />
      ) : (
        <div className="stack-sm">
          {levels.map((level, index) => (
            <div key={level.id ?? `${tone}-${index}`} className="obr">
              <span className={tone === 'bid' ? 'orderbook-price obp-bid' : 'orderbook-price obp-ask'}>
                {level.priceLabel}
              </span>
              <span>{level.quantityLabel}</span>
              <span>{level.orderCountLabel}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function MatchingOrderBookPanel({ model }: Props) {
  return (
    <SectionFrame
      title={model.title}
      description={model.description}
    >
      <div className="obs-grid">
        <GlassPanel className="obs-card" tone="subtle">
          <p className="subtle-label">{model.bestBidTitle}</p>
          <p className="obs-value obs-value-bid">{model.bestBidLabel}</p>
        </GlassPanel>
        <GlassPanel className="obs-card" tone="subtle">
          <p className="subtle-label">{model.bestAskTitle}</p>
          <p className="obs-value obs-value-ask">{model.bestAskLabel}</p>
        </GlassPanel>
        <GlassPanel className="obs-card" tone="subtle">
          <p className="subtle-label">{model.spreadTitle}</p>
          <p className="obs-value">{model.spreadLabel}</p>
        </GlassPanel>
      </div>

      <div className="obgrid" data-testid="matching-orderbook-panel">
        <LevelGroup
          title={model.bidsTitle}
          levels={model.bids}
          tone="bid"
          emptyTitle={model.emptyTitle}
          emptyBody={model.emptyBody}
        />
        <LevelGroup
          title={model.asksTitle}
          levels={model.asks}
          tone="ask"
          emptyTitle={model.emptyTitle}
          emptyBody={model.emptyBody}
        />
      </div>
      <GlassPanel className="obf" tone="subtle" padded={false}>
        <div className="obfc">
          <p className="obu">{model.updatedTitle}: {model.updatedAtLabel}</p>
          <p className="obu">{model.depthBalanceTitle}: {model.depthBalanceLabel}</p>
        </div>
        {model.stale && model.staleHint ? <p className="obst">{model.staleHint}</p> : null}
      </GlassPanel>
    </SectionFrame>
  )
}
