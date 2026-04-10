import { beforeEach, describe, expect, it } from 'vitest'

import { useCerberusStore } from '.'

const EMPTY_STATUS = {
  state: 'idle' as const,
  last_update_ms: null,
  stale: true,
  request_id: undefined,
}

const EMPTY_FLOW = {
  state: 'idle' as const,
  last_update_ms: null,
  reason: undefined,
  request_id: undefined,
}

describe('ui state machine', () => {
  beforeEach(() => {
    useCerberusStore.setState((state) => ({
      ...state,
      uiState: {
        ...state.uiState,
        domain_status: {
          'market-stream': { ...EMPTY_STATUS },
          'strategy-summary': { ...EMPTY_STATUS },
          'execution-trading': { ...EMPTY_STATUS },
        },
        core_flow: {
          bootstrap: { ...EMPTY_FLOW },
          market: { ...EMPTY_FLOW },
          precheck: { ...EMPTY_FLOW },
          submit: { ...EMPTY_FLOW },
          feedback: { ...EMPTY_FLOW },
          cancel: { ...EMPTY_FLOW },
        },
        shell_navigation: {
          workspace: 'overview',
          panel: 'home',
        },
      },
    }))
  })

  it('transitions from loading to ready', () => {
    const { uiActions } = useCerberusStore.getState()
    uiActions.setDomainStatus('market-stream', { state: 'loading', stale: false })
    uiActions.setDomainStatus('market-stream', { state: 'ready', stale: false })

    const status = useCerberusStore.getState().uiState.domain_status['market-stream']
    expect(status.state).toBe('ready')
    expect(status.stale).toBe(false)
    expect(typeof status.last_update_ms).toBe('number')
  })

  it('marks stale domain as degraded', () => {
    const { uiActions } = useCerberusStore.getState()
    const past = Date.now() - 20_000
    uiActions.setDomainStatus('strategy-summary', {
      state: 'ready',
      stale: false,
      last_update_ms: past,
    })
    uiActions.recomputeStaleFlags(Date.now())

    const status = useCerberusStore.getState().uiState.domain_status['strategy-summary']
    expect(status.stale).toBe(true)
    expect(status.state).toBe('degraded')

    const flow = useCerberusStore.getState().uiState.core_flow.bootstrap
    expect(flow.state).toBe('degraded')
    expect(flow.reason).toBe('stale data')
  })

  it('maps strategy domain success into bootstrap flow state', () => {
    const { uiActions } = useCerberusStore.getState()
    uiActions.setDomainStatus('strategy-summary', { state: 'ready', stale: false })

    const flow = useCerberusStore.getState().uiState.core_flow.bootstrap
    expect(flow.state).toBe('success')
    expect(flow.last_update_ms).not.toBeNull()
  })

  it('stores request_id when core flow step is updated directly', () => {
    const { uiActions } = useCerberusStore.getState()
    uiActions.setCoreFlowStep('submit', {
      state: 'success',
      reason: 'order submit accepted',
      request_id: 'rid-submit-001',
    })

    const flow = useCerberusStore.getState().uiState.core_flow.submit
    expect(flow.state).toBe('success')
    expect(flow.request_id).toBe('rid-submit-001')
  })

  it('propagates request_id from domain status to core flow', () => {
    const { uiActions } = useCerberusStore.getState()
    uiActions.setDomainStatus('execution-trading', {
      state: 'degraded',
      stale: true,
      reason: 'request timeout',
      request_id: 'rid-exec-404',
    })

    const status = useCerberusStore.getState().uiState.domain_status['execution-trading']
    const flow = useCerberusStore.getState().uiState.core_flow.feedback
    expect(status.request_id).toBe('rid-exec-404')
    expect(flow.request_id).toBe('rid-exec-404')
  })

  it('updates shell workspace through ui actions', () => {
    const { uiActions } = useCerberusStore.getState()
    uiActions.setWorkspace('inference')

    expect(useCerberusStore.getState().uiState.shell_navigation.workspace).toBe('inference')
    expect(useCerberusStore.getState().uiState.shell_navigation.panel).toBe('home')
  })

  it('updates shell workspace panel through ui actions', () => {
    const { uiActions } = useCerberusStore.getState()
    uiActions.setWorkspacePanel('execution', 'order')

    expect(useCerberusStore.getState().uiState.shell_navigation).toEqual({
      workspace: 'execution',
      panel: 'order',
    })
  })
})
