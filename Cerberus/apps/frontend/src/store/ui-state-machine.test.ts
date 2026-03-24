import { beforeEach, describe, expect, it } from 'vitest'

import { useCerberusStore } from '.'

const EMPTY_STATUS = {
  state: 'idle' as const,
  last_update_ms: null,
  stale: true,
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
  })
})
