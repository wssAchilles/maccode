import { useEffect, useEffectEvent, useRef } from 'react'

import { useCerberusStore } from '../../store'

type Params = {
  enabled: boolean
}

export function useAppBootstrap({ enabled }: Params) {
  const connectMarketSocket = useCerberusStore((state) => state.marketStreamActions.connectMarketSocket)
  const connectOrdersSocket = useCerberusStore((state) => state.executionTradingActions.connectOrdersSocket)
  const recomputeStaleFlags = useCerberusStore((state) => state.uiActions.recomputeStaleFlags)
  const setCoreFlowStep = useCerberusStore((state) => state.uiActions.setCoreFlowStep)
  const bootstrappedRef = useRef(false)

  const handleRecompute = useEffectEvent(() => {
    recomputeStaleFlags()
  })

  useEffect(() => {
    if (!enabled) {
      bootstrappedRef.current = false
      return
    }

    setCoreFlowStep('bootstrap', {
      state: 'active',
      reason: 'initializing workbench shell',
    })

    if (!bootstrappedRef.current) {
      connectMarketSocket()
      connectOrdersSocket()
      bootstrappedRef.current = true
      setCoreFlowStep('bootstrap', {
        state: 'success',
        reason: 'shell ready',
      })
    }

    const staleTimer = window.setInterval(() => {
      handleRecompute()
    }, 2_000)

    return () => {
      window.clearInterval(staleTimer)
    }
  }, [connectMarketSocket, connectOrdersSocket, enabled, handleRecompute, setCoreFlowStep])
}
