import type { ReactNode } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { I18nProvider } from '../../i18n/I18nProvider'
import { buildPreparedExecutionSelection } from '../execution/read-models'
import { ExecutionLifecyclePanel } from './components/ExecutionLifecyclePanel'
import { StrategyPortfolioPanel } from './components/StrategyPortfolioPanel'
import { StrategyRegistryPanel } from './components/StrategyRegistryPanel'
import {
  buildExecutionLifecyclePanelModel,
  buildStrategyPortfolioPanelModel,
  buildStrategyRegistryPanelModel,
} from './view-models'

function renderWithI18n(ui: ReactNode) {
  return render(<I18nProvider>{ui}</I18nProvider>)
}

describe('strategy orchestration module', () => {
  it('builds portfolio summary with gate, consensus, and tracked symbol chips', async () => {
    const onSelectSymbol = vi.fn()
    const model = buildStrategyPortfolioPanelModel({
      t: (key) => key,
      selectedSymbol: 'BTCUSDT',
      signal: {
        status: 'ready',
        signal: 'BUY',
        confidence: 0.82,
        portfolio: {
          symbol: 'BTCUSDT',
          dominant_signal: 'BUY',
          final_signal: 'BUY',
          final_source: 'rule_engine',
          signal_bias: 'bullish',
          consensus_level: 'moderate',
          execution_ready: false,
          execution_gate: 'review',
          execution_gate_reason: 'strategy basket is still contested',
          lead_strategy_id: 'default',
          lead_strategy_label: 'Rule engine',
          aligned_count: 1,
          contested_count: 1,
          agreement_ratio: 0.5,
          weighted_score: 0.564,
          active_strategy_count: 2,
          tracked_symbols: ['BTCUSDT', 'ETHUSDT'],
          updated_at: '2026-03-30T10:00:00Z',
          latest_price: 101.25,
        },
      },
    })

    renderWithI18n(<StrategyPortfolioPanel model={model} onSelectSymbol={onSelectSymbol} />)

    expect(screen.getAllByText(/workspace\.strategy\.gate\.review/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/workspace\.strategy\.consensus\.moderate/i)).toBeTruthy()

    await userEvent.click(screen.getByRole('button', { name: 'ETHUSDT' }))
    expect(onSelectSymbol).toHaveBeenCalledWith('ETHUSDT')
  })

  it('formats numeric portfolio timestamps into human-readable labels', () => {
    const model = buildStrategyPortfolioPanelModel({
      t: (key) => key,
      selectedSymbol: 'BTCUSDT',
      signal: {
        status: 'ready',
        signal: 'BUY',
        confidence: 0.82,
        portfolio: {
          symbol: 'BTCUSDT',
          dominant_signal: 'BUY',
          final_signal: 'BUY',
          final_source: 'rule_engine',
          signal_bias: 'bullish',
          consensus_level: 'moderate',
          execution_ready: false,
          execution_gate: 'review',
          execution_gate_reason: 'strategy basket is still contested',
          lead_strategy_id: 'default',
          lead_strategy_label: 'Rule engine',
          aligned_count: 1,
          contested_count: 1,
          agreement_ratio: 0.5,
          weighted_score: 0.564,
          active_strategy_count: 2,
          tracked_symbols: ['BTCUSDT', 'ETHUSDT'],
          updated_at: Date.parse('2026-04-01T10:00:00Z') as unknown as string,
          latest_price: 101.25,
        },
      },
    })

    expect(model.items.find((item) => item.id === 'updatedAt')?.value).not.toBe('1775037600000')
    expect(model.items.find((item) => item.id === 'updatedAt')?.value).toMatch(/2026/)
  })

  it('renders execution lifecycle stages with progression context', () => {
    const preparedSelection = buildPreparedExecutionSelection(
      [
        {
          id: 'evt-1',
          channel: 'trade.executions.default',
          payload: {},
          received_at: Date.now(),
          event_type: 'matching.execution.filled',
          symbol: 'BTCUSDT',
          order_id: 'ord-1',
          execution_id: 'exec-1',
          request_id: 'rid-1',
          status: 'filled',
        },
      ],
      'BTCUSDT',
    )
    const model = buildExecutionLifecyclePanelModel({
      t: (key) => key,
      signal: {
        status: 'ready',
        signal: 'BUY',
        confidence: 0.84,
        decision_source: 'rule_engine',
        dispatch_state: 'accepted',
        portfolio: {
          symbol: 'BTCUSDT',
          dominant_signal: 'BUY',
          final_signal: 'BUY',
          final_source: 'rule_engine',
          signal_bias: 'bullish',
          consensus_level: 'high',
          execution_ready: true,
          execution_gate: 'ready',
          execution_gate_reason: 'basket supports live execution',
          aligned_count: 2,
          contested_count: 0,
          weighted_score: 0.91,
          active_strategy_count: 2,
          tracked_symbols: ['BTCUSDT'],
        },
      },
      preparedSelection,
      persistenceStatus: {
        status: 'ok',
        worker: {
          processed_ticks: 12,
          forwarded_executions: 3,
          last_execution_id: 33,
          has_last_signal: true,
        },
        matching: {
          stats: {
            enabled: true,
            live_orders: 2,
            trade_count: 5,
            tracked_orders: 2,
            rejected_orders: 0,
            symbols: 1,
          },
        },
        stores: {
          supabase_enabled: true,
          firebase_enabled: false,
          supabase_table: 'signals',
          firebase_collection: 'signals',
        },
      },
      latestEventSummary: 'matching.execution.filled · BTCUSDT · FILLED',
      heartbeat: undefined,
      tradingPolicy: {
        enforced: true,
        binance_allowed_symbols: ['BTCUSDT'],
        alpaca_allowed_symbols: [],
      },
      binanceRule: {
        symbol: 'BTCUSDT',
        min_qty: 0.001,
        step_size: 0.001,
        min_notional: 5,
        refreshed_at: Date.now(),
      },
      domainStatus: {
        state: 'ready',
        last_update_ms: Date.now(),
        stale: false,
      },
    })

    renderWithI18n(<ExecutionLifecyclePanel model={model} />)

    expect(screen.getByText(/workspace\.execution\.lifecycleStageDispatch/i)).toBeTruthy()
    expect(screen.getByText(/workspace\.execution\.lifecycleStageExecution/i)).toBeTruthy()
    expect(screen.getByText('Recent identifiers')).toBeTruthy()
    expect(screen.getByText('Execution telemetry')).toBeTruthy()
    expect(screen.getByText(/workspace\.execution\.lifecycleLiveOrders/i)).toBeTruthy()
    expect(screen.getByText(/workspace\.execution\.lifecycleExecutionId/i)).toBeTruthy()
  })

  it('builds strategy registry panel with enabled entries and coverage', () => {
    const model = buildStrategyRegistryPanelModel({
      t: (key) => key,
      selectedSymbol: 'BTCUSDT',
      signal: {
        status: 'ready',
        signal: 'BUY',
        confidence: 0.82,
        strategy_registry: {
          symbol: 'BTCUSDT',
          tracked_symbols: ['BTCUSDT', 'ETHUSDT'],
          conflict_policy: 'review_on_conflict',
          downgrade_policy: 'review',
          entries: [
            {
              strategy_id: 'default',
              label: 'Rule engine',
              engine: 'moving_average',
              source: 'rule_engine',
              role: 'baseline',
              enabled: true,
              priority: 1,
              configured_weight: 0.62,
              effective_weight: 0.62,
              symbol_coverage: ['BTCUSDT', 'ETHUSDT'],
              conflict_targets: ['inference'],
              conflict_policy: 'review_on_conflict',
              downgrade_policy: 'review',
              downgrade_action: 'review',
              metadata: {},
            },
          ],
        },
      },
    })

    renderWithI18n(<StrategyRegistryPanel model={model} />)

    expect(screen.getByText('Rule engine')).toBeTruthy()
    expect(screen.getAllByText(/common\.ready/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/workspace\.strategy\.configuredWeight/i)).toBeTruthy()
  })
})
