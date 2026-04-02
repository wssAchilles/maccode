import { act, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { I18nProvider } from '../i18n/I18nProvider'
import { useCerberusStore } from '../store'
import { ExecutionTimelinePanel } from './ExecutionTimelinePanel'

vi.mock('../app/bootstrap/useResourceQueries', () => ({
  useRecentEventsResource: vi.fn(),
}))

describe('ExecutionTimelinePanel', () => {
  const initialState = useCerberusStore.getState()
  const originalResizeObserver = globalThis.ResizeObserver

  beforeEach(() => {
    vi.stubGlobal('ResizeObserver', undefined)
    useCerberusStore.setState((state) => ({
      ...state,
      executionTrading: {
        ...state.executionTrading,
        order_events: [
          {
            id: 'evt-1',
            channel: 'trade.executions.default',
            payload: {},
            received_at: Date.parse('2026-04-01T14:28:31.000Z'),
            event_time: '1775024608568',
            event_type: 'strategy.signal.generated',
            lifecycle_phase: 'submit',
            symbol: 'BTCUSDT',
            account_id: 'default',
            status: 'accepted',
            order_id: 'default-order-0000000442-order-id',
            request_id: '143e0a7e49624402b69f5ed59d53e19c-request-id',
            client_order_id: 'default-BTCUSDT-1775024608568-BUY-client-order-id',
            execution_id: 'p784af461abd47bea136bd7c4391f4dc-execution-id',
            correlation_key: 'corr-1',
          },
        ],
        filter_symbol: 'ALL',
        filter_account_id: 'ALL',
        filter_status: 'ALL',
      },
      uiState: {
        ...state.uiState,
        domain_status: {
          ...state.uiState.domain_status,
          'execution-trading': {
            ...state.uiState.domain_status['execution-trading'],
            state: 'ready',
            stale: false,
            reason: undefined,
          },
        },
      },
    }))
  })

  afterEach(() => {
    useCerberusStore.setState(initialState, true)
    if (originalResizeObserver) {
      vi.stubGlobal('ResizeObserver', originalResizeObserver)
    } else {
      vi.unstubAllGlobals()
    }
    vi.clearAllMocks()
  })

  it('renders compact timeline metadata in a scrollable viewport', async () => {
    let container!: HTMLElement

    await act(async () => {
      const view = render(
        <I18nProvider>
          <ExecutionTimelinePanel active />
        </I18nProvider>,
      )
      container = view.container
      await new Promise((resolve) => setTimeout(resolve, 0))
    })

    await waitFor(() => {
      expect(screen.getByTestId('execution-timeline-panel')).toBeTruthy()
      expect(container.querySelector('.xtm-list')).toBeTruthy()
      expect(container.querySelectorAll('.tr-meta-line')).toHaveLength(4)
      expect(screen.getByTitle('default-order-00…order-id')).toBeTruthy()
      expect(screen.getByTitle('143e0a7e49624402…quest-id')).toBeTruthy()
    })
  })
})
