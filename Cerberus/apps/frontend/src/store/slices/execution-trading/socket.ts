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

  onLoading()
  ordersSocket = new WebSocket(`${wsBase}/ws/orders`)

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
    onDegraded('orders websocket closed')
  }
}
