import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { MatchingOrderBookPanel } from './MatchingOrderBookPanel'
import { buildMatchingOrderBookPanelModel } from '../view-models/orderbook'
import type { MatchingOrderBook } from '../types/contracts'

const t = (key: string) => key

describe('MatchingOrderBookPanel', () => {
  it('renders stable column headers and scrollable level groups', () => {
    const orderbook: MatchingOrderBook = {
      enabled: true,
      degraded: false,
      symbol: 'BTCUSDT',
      depth: 10,
      generated_at_ms: Date.parse('2026-04-01T08:00:00.000Z'),
      bids: [{ price: 100.123456, total_quantity: 3.5, order_count: 2 }],
      asks: [{ price: 100.223456, total_quantity: 4.25, order_count: 3 }],
    }

    const model = buildMatchingOrderBookPanelModel({ t, orderbook })
    const { container } = render(<MatchingOrderBookPanel model={model} />)

    expect(screen.getAllByText('orderbook.priceColumn').length).toBe(2)
    expect(screen.getAllByText('orderbook.quantityColumn').length).toBe(2)
    expect(screen.getAllByText('orderbook.orderCountColumn').length).toBe(2)
    expect(screen.getByTestId('matching-orderbook-panel')).toBeTruthy()
    expect(container.querySelectorAll('.obg-list')).toHaveLength(2)
  })
})
