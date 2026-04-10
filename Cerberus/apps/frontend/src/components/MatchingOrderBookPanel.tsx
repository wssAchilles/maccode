import type { ReactNode } from 'react'

import type { MatchingOrderBookLevelRowModel, MatchingOrderBookPanelModel } from '../view-models/orderbook'
import { EmptyState, GlassPanel, PanelSection, SectionFrame, TerminalBand } from '../ui'

type Props = {
  model: MatchingOrderBookPanelModel
  aside?: ReactNode
  className?: string
  descriptionMode?: 'visible' | 'srOnly' | 'hidden'
}

function LevelGroup({
  title,
  levels,
  tone,
  emptyTitle,
  emptyBody,
  priceColumnTitle,
  quantityColumnTitle,
  orderCountColumnTitle,
}: {
  title: string
  levels: MatchingOrderBookLevelRowModel[]
  tone: 'bid' | 'ask'
  emptyTitle: string
  emptyBody: string
  priceColumnTitle: string
  quantityColumnTitle: string
  orderCountColumnTitle: string
}) {
  return (
    <div className="obg">
      <p className="subtle-label">{title}</p>
      {levels.length === 0 ? (
        <EmptyState title={emptyTitle} body={emptyBody} />
      ) : (
        <div className="obg-viewport">
          <div className="obr obr-head" aria-hidden="true">
            <span className="obc obc-price">{priceColumnTitle}</span>
            <span className="obc obc-qty">{quantityColumnTitle}</span>
            <span className="obc obc-count">{orderCountColumnTitle}</span>
          </div>
          <div className="obg-list" role="list" aria-label={title}>
            {levels.map((level, index) => (
              <div key={level.id ?? `${tone}-${index}`} className="obr" role="listitem">
                <span className={tone === 'bid' ? 'obc obc-price orderbook-price obp-bid' : 'obc obc-price orderbook-price obp-ask'}>
                  {level.priceLabel}
                </span>
                <span className="obc obc-qty">{level.quantityLabel}</span>
                <span className="obc obc-count">{level.orderCountLabel}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function MatchingOrderBookPanel({ model, aside, className, descriptionMode = 'visible' }: Props) {
  return (
    <SectionFrame
      title={model.title}
      description={model.description}
      descriptionMode={descriptionMode}
      aside={aside}
      className={className}
    >
      <TerminalBand model={model.band} className="ob-band" compact hideHint hideEyebrow />
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
          <p className="subtle-label">{model.midPriceTitle}</p>
          <p className="obs-value">{model.midPriceLabel}</p>
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
          priceColumnTitle={model.priceColumnTitle}
          quantityColumnTitle={model.quantityColumnTitle}
          orderCountColumnTitle={model.orderCountColumnTitle}
        />
        <LevelGroup
          title={model.asksTitle}
          levels={model.asks}
          tone="ask"
          emptyTitle={model.emptyTitle}
          emptyBody={model.emptyBody}
          priceColumnTitle={model.priceColumnTitle}
          quantityColumnTitle={model.quantityColumnTitle}
          orderCountColumnTitle={model.orderCountColumnTitle}
        />
      </div>
      <PanelSection
        className="obf"
        title={model.totalDepthLabel}
        compact
      >
        <div className="obfc">
          <div className="obs-card obu">
            <p className="subtle-label">{model.updatedTitle}</p>
            <p className="obu-value">{model.updatedAtLabel}</p>
          </div>
          <div className="obs-card obu">
            <p className="subtle-label">{model.depthBalanceTitle}</p>
            <p className="obu-value">{model.depthBalanceLabel}</p>
          </div>
          <div className="obs-card obu">
            <p className="subtle-label">{model.totalDepthTitle}</p>
            <p className="obu-value">{model.totalDepthLabel}</p>
          </div>
          <div className="obs-card obu">
            <p className="subtle-label">{model.liquidityBiasTitle}</p>
            <p className="obu-value">{model.liquidityBiasLabel}</p>
          </div>
        </div>
        {model.stale && model.staleHint ? <p className="obst">{model.staleHint}</p> : null}
      </PanelSection>
    </SectionFrame>
  )
}
