import { describe, expect, it } from 'vitest'

import type { CoreFlowMap } from '../store/slices/shared'
import { buildCoreFlowPanelModel, formatDateTimeLabel } from './workbench'

const t = (key: string) => key

describe('workbench view models', () => {
  it('prepares a core flow panel model with counts and formatted steps', () => {
    const flow: CoreFlowMap = {
      bootstrap: { state: 'success', last_update_ms: 1_000, reason: 'bootstrap_ready', request_id: 'req-bootstrap' },
      market: { state: 'active', last_update_ms: 2_000, reason: 'market_sync' },
      precheck: { state: 'error', last_update_ms: 3_000, reason: 'precheck_failed', request_id: 'req-precheck' },
      submit: { state: 'idle', last_update_ms: null },
      feedback: { state: 'idle', last_update_ms: null },
      cancel: { state: 'idle', last_update_ms: null },
    }

    const model = buildCoreFlowPanelModel(flow, t)

    expect(model.summary).toBe('1 common.ready · 1 health.state.loading · 1 workspace.overview.attention')
    expect(model.hint).toContain('common.updatedAt:')
    expect(model.steps[0]).toMatchObject({
      id: 'bootstrap',
      title: 'flow.step.bootstrap',
      indexLabel: '1.',
      state: 'success',
      stateLabel: 'health.state.ready',
      reason: 'bootstrap_ready',
      requestId: 'req-bootstrap',
    })
    expect(model.steps[2]).toMatchObject({
      id: 'precheck',
      state: 'error',
      reason: 'precheck_failed',
      requestId: 'req-precheck',
    })
    expect(model.steps[0]?.updatedAt).not.toBe('—')
  })

  it('formats numeric-string timestamps as local date time labels', () => {
    expect(formatDateTimeLabel('1775036445252')).toMatch(/2026/)
  })

  it('formats ISO timestamps and guards invalid values', () => {
    expect(formatDateTimeLabel('2026-04-01T10:00:00Z')).toMatch(/2026/)
    expect(formatDateTimeLabel('not-a-date')).toBe('not-a-date')
    expect(formatDateTimeLabel(undefined)).toBe('—')
  })
})
