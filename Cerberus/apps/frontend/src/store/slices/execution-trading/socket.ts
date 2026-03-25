import type { OrderTimelineEvent } from '../../../types/contracts'
import { parseOrdersSocketMessage } from './events'

type ConnectOrdersSocketParams = {
  liveStreamEnabled: boolean
  wsBase: string
  onLoading: () => void
  onHeartbeat: (message: string) => void
  onEvent: (event: OrderTimelineEvent) => void
  onDegraded: (reason: string) => void
}

let ordersSocket: WebSocket | null = null
let ordersReconnectHandle: number | null = null
let ordersReconnectAttempt = 0

const MAX_ORDERS_RECONNECT_DELAY_MS = 30_000

function clearOrdersReconnectHandle(): void {
  if (ordersReconnectHandle !== null) {
    window.clearTimeout(ordersReconnectHandle)
    ordersReconnectHandle = null
  }
}

export function connectOrdersSocket({
  liveStreamEnabled,
  wsBase,
  onLoading,
  onHeartbeat,
  onEvent,
  onDegraded,
}: ConnectOrdersSocketParams): void {
  if (!liveStreamEnabled || ordersSocket) {
    return
  }

  clearOrdersReconnectHandle()
  onLoading()
  ordersSocket = new WebSocket(`${wsBase}/ws/orders`)

  ordersSocket.onopen = () => {
    ordersReconnectAttempt = 0
  }

  ordersSocket.onmessage = (event) => {
    const parsed = parseOrdersSocketMessage(String(event.data))
    if (parsed.kind === 'heartbeat') {
      onHeartbeat(parsed.message)
      return
    }
    if (parsed.kind === 'event') {
      onEvent(parsed.event)
      return
    }
    if (parsed.kind === 'raw') {
      onHeartbeat(parsed.message)
    }
  }

  ordersSocket.onerror = () => {
    onDegraded('orders websocket error')
  }

  ordersSocket.onclose = () => {
    ordersSocket = null
    if (!liveStreamEnabled || ordersReconnectHandle !== null) {
      onDegraded('orders websocket closed')
      return
    }

    const delayMs = Math.min(MAX_ORDERS_RECONNECT_DELAY_MS, 1_000 * 2 ** Math.min(ordersReconnectAttempt, 5))
    ordersReconnectAttempt += 1
    onDegraded(`orders websocket closed, reconnect in ${Math.round(delayMs / 1_000)}s`)
    ordersReconnectHandle = window.setTimeout(() => {
      ordersReconnectHandle = null
      connectOrdersSocket({
        liveStreamEnabled,
        wsBase,
        onLoading,
        onHeartbeat,
        onEvent,
        onDegraded,
      })
    }, delayMs)
  }
}
