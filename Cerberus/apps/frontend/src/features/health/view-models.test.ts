import { describe, expect, it } from 'vitest'

import {
  buildHealthDiagnostics,
  buildServiceHealthPanelModel,
  buildHealthStoreItems,
  buildHealthWorkerItems,
} from './view-models'

const t = (key: string) => key

describe('health view models', () => {
  it('builds worker and store panels from persistence status', () => {
    const persistenceStatus = {
      status: 'ok',
      worker: {
        processed_ticks: 12,
        tracked_symbols: ['BTCUSDT', 'ETHUSDT'],
        started: true,
        has_last_signal: true,
      },
      stores: {
        supabase_enabled: true,
        firebase_enabled: false,
        supabase_table: 'strategy_signals',
        firebase_collection: 'signals',
      },
      matching: {
        health: {
          enabled: true,
          reachable: true,
          status: 'ok',
          service: 'matching-cpp',
          version: '0.1.0',
          uptime_seconds: 30,
        },
      },
    } as const

    expect(buildHealthWorkerItems({ t, persistenceStatus })).toEqual([
      { id: 'processed', label: 'strategy.ticksProcessed', value: '12' },
      { id: 'trackedSymbols', label: 'workspace.health.trackedSymbols', value: '2' },
      { id: 'started', label: 'workspace.health.workerStarted', value: 'true' },
    ])
    expect(buildHealthStoreItems({ t, persistenceStatus })).toEqual([
      { id: 'supabase', label: 'Supabase', value: 'true' },
      { id: 'firebase', label: 'Firestore', value: 'false' },
      { id: 'matching', label: 'strategy.matching', value: 'ok' },
    ])
  })

  it('builds diagnostics from summary error and domain status', () => {
    const diagnostics = buildHealthDiagnostics(
      { code: 'summary_failed', message: 'summary unavailable', request_id: 'rid-1' },
      {
        strategy: {
          state: 'degraded',
          last_update_ms: 1000,
          stale: false,
          request_id: 'rid-2',
        },
      },
    )

    expect(diagnostics.summaryError?.code).toBe('summary_failed')
    expect(diagnostics.domainStatus.strategy.state).toBe('degraded')
  })

  it('prepares the service health panel payload outside render', () => {
    const model = buildServiceHealthPanelModel({
      t,
      domainStatus: {
        'market-stream': {
          state: 'ready',
          last_update_ms: 1_000,
          stale: false,
          request_id: 'rid-market',
        },
        'strategy-summary': {
          state: 'degraded',
          last_update_ms: 2_000,
          stale: true,
          reason: 'summary lagging',
        },
        'execution-trading': {
          state: 'idle',
          last_update_ms: null,
          stale: false,
        },
      },
      persistenceStatus: {
        status: 'ok',
        worker: {
          processed_ticks: 12,
          tracked_symbols: ['BTCUSDT'],
          started: true,
          has_last_signal: true,
        },
        stores: {
          supabase_enabled: true,
          firebase_enabled: false,
          supabase_table: 'strategy_signals',
          firebase_collection: 'signals',
        },
        matching: {
          health: {
            enabled: true,
            reachable: true,
            status: 'ok',
            service: 'matching-cpp',
            version: '0.1.0',
            uptime_seconds: 30,
          },
          stats: {
            enabled: true,
            live_orders: 2,
            trade_count: 3,
            tracked_orders: 2,
            rejected_orders: 0,
            symbols: 1,
          },
        },
      },
    })

    expect(model.cards).toHaveLength(3)
    expect(model.updatedAtLabel).toBe('common.updatedAt')
    expect(model.requestIdLabel).toBe('health.requestId')
    expect(model.persistenceGroups[0][0]).toEqual({
      id: 'status',
      label: 'strategy.persistence',
      value: 'ok',
    })
    expect(model.persistenceGroups[1][1]).toEqual({
      id: 'liveOrders',
      label: 'Live orders',
      value: '2',
    })
  })
})
