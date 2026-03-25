import type { Page, Request, Response } from '@playwright/test'

const CORE_ENDPOINT_PARTS = [
  '/api/v1/strategy/summary',
  '/api/v1/klines',
  '/api/v1/binance/symbol-rules',
  '/api/v1/trading/policy',
  '/api/v1/binance/order/test',
  '/api/v1/alpaca/orders',
  '/api/v1/orders/events/recent',
]

const REQUIRED_ENDPOINT_PARTS = [
  '/api/v1/strategy/summary',
  '/api/v1/klines',
  '/api/v1/binance/symbol-rules',
  '/api/v1/trading/policy',
  '/api/v1/binance/order/test',
  '/api/v1/alpaca/orders',
  '/api/v1/orders/events/recent',
]

const CORE_WS_PARTS = ['/ws/market', '/ws/orders']
const REQUEST_TIMEOUT_MS = 8_000

function matchPart(url: string, parts: readonly string[]): string | undefined {
  return parts.find((part) => url.includes(part))
}

function shouldTrackRequest(request: Request): boolean {
  const url = request.url()
  return Boolean(matchPart(url, CORE_ENDPOINT_PARTS)) || Boolean(matchPart(url, CORE_WS_PARTS))
}

export type DeployGateObserver = {
  attach: (page: Page) => void
  assertNoFailures: () => void
}

export function createDeployGateObserver(): DeployGateObserver {
  const consoleErrors: string[] = []
  const failedRequests: string[] = []
  const badResponses: string[] = []
  const slowResponses: string[] = []
  const wsSeen = new Set<string>()
  const apiSeen = new Set<string>()
  const requestStartAt = new Map<Request, number>()

  const handleRequest = (request: Request) => {
    if (!shouldTrackRequest(request)) {
      return
    }
    requestStartAt.set(request, Date.now())
  }

  const handleResponse = (response: Response) => {
    const url = response.url()
    const apiPart = matchPart(url, CORE_ENDPOINT_PARTS)
    if (!apiPart) {
      return
    }
    apiSeen.add(apiPart)
    const request = response.request()
    const startedAt = requestStartAt.get(request)
    if (startedAt) {
      const latencyMs = Date.now() - startedAt
      if (latencyMs > REQUEST_TIMEOUT_MS) {
        slowResponses.push(`[${latencyMs}ms] ${apiPart} -> ${url}`)
      }
      requestStartAt.delete(request)
    }
    if (response.status() >= 400) {
      badResponses.push(`[${response.status()}] ${apiPart} -> ${url}`)
    }
  }

  const handleRequestFailed = (request: Request) => {
    if (!shouldTrackRequest(request)) {
      return
    }
    const failure = request.failure()
    failedRequests.push(`[${failure?.errorText ?? 'request_failed'}] ${request.url()}`)
  }

  return {
    attach: (page: Page) => {
      page.on('request', handleRequest)
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text())
        }
      })
      page.on('response', handleResponse)
      page.on('requestfailed', handleRequestFailed)
      page.on('websocket', (socket) => {
        const part = matchPart(socket.url(), CORE_WS_PARTS)
        if (part) {
          wsSeen.add(part)
        }
      })
    },
    assertNoFailures: () => {
      if (consoleErrors.length > 0) {
        throw new Error(`console errors detected:\n${consoleErrors.join('\n')}`)
      }
      if (failedRequests.length > 0) {
        throw new Error(`core request failures detected:\n${failedRequests.join('\n')}`)
      }
      if (badResponses.length > 0) {
        throw new Error(`core endpoint 4xx/5xx detected:\n${badResponses.join('\n')}`)
      }
      if (slowResponses.length > 0) {
        throw new Error(
          `core endpoint timeout threshold exceeded (> ${REQUEST_TIMEOUT_MS}ms):\n${slowResponses.join('\n')}`,
        )
      }
      for (const apiPath of REQUIRED_ENDPOINT_PARTS) {
        if (!apiSeen.has(apiPath)) {
          throw new Error(`core endpoint not observed: ${apiPath}`)
        }
      }
      for (const wsPath of CORE_WS_PARTS) {
        if (!wsSeen.has(wsPath)) {
          throw new Error(`core websocket not observed: ${wsPath}`)
        }
      }
    },
  }
}
