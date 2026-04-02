import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import { I18nProvider } from '../../i18n/I18nProvider'
import { buildPreparedExecutionSelection } from './read-models'
import { ExecutionOperationsPanel } from './components/ExecutionOperationsPanel'
import { buildExecutionOperationsPanel } from './view-models'

describe('Execution operations panel', () => {
  it('builds OMS/EMS summary for the active symbol', () => {
    const preparedSelection = buildPreparedExecutionSelection(
      [
        {
          id: 'evt-1',
          event_type: 'matching.order.submitted',
          symbol: 'BTCUSDT',
          status: 'accepted',
          request_id: 'req-1',
          order_id: 'ord-1',
          execution_id: 'exe-1',
          lifecycle_phase: 'accepted',
          correlation_key: 'ord-1',
          received_at: '2026-03-31T08:00:00Z',
        },
        {
          id: 'evt-2',
          event_type: 'matching.order.rejected',
          symbol: 'BTCUSDT',
          status: 'rejected',
          request_id: 'req-2',
          order_id: 'ord-2',
          lifecycle_phase: 'rejected',
          correlation_key: 'ord-2',
          received_at: '2026-03-31T08:01:00Z',
        },
      ],
      'BTCUSDT',
    )

    const model = buildExecutionOperationsPanel({
      t: (key) => key,
      selectedSymbol: 'BTCUSDT',
      preparedSelection,
      persistenceStatus: {
        status: 'ok',
        worker: {
          processed_ticks: 10,
          forwarded_executions: 1,
          last_execution_id: 9,
          has_last_signal: true,
        },
        matching: {
          stats: {
            enabled: true,
            live_orders: 2,
            trade_count: 3,
            tracked_orders: 2,
            rejected_orders: 1,
            symbols: 1,
          },
        },
        stores: {
          supabase_enabled: false,
          firebase_enabled: false,
          supabase_table: 'signals',
          firebase_collection: 'signals',
        },
      },
      domainStatus: { state: 'ready', stale: false },
    })

    render(
      <I18nProvider>
        <ExecutionOperationsPanel model={model} />
      </I18nProvider>,
    )

    expect(screen.getByText('Execution operations')).toBeInTheDocument()
    expect(screen.getByText('BTCUSDT · 2 workspace.execution.operationsSummarySuffix')).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Execution pulse' })).toBeInTheDocument()
    expect(screen.getByText('Latency snapshot')).toBeInTheDocument()
    expect(screen.getByText('Venue pulse')).toBeInTheDocument()
    expect(screen.getByText('Lifecycle distribution')).toBeInTheDocument()
    expect(screen.getByText('workspace.execution.operationsRejected: 1')).toBeInTheDocument()
    expect(screen.getAllByText('2').length).toBeGreaterThan(0)
  })
})
