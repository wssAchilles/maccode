import { normalizeError } from '../../lib/http'
import { buildRequestHeaders } from '../../lib/auth-session'
import type { GatewayResponse } from './types'

export async function callGateway(path: string, gatewayBase: string, init?: RequestInit): Promise<GatewayResponse> {
  const url = `${gatewayBase}${path}`
  try {
    const headers = await buildRequestHeaders(init?.headers)
    const response = await fetch(url, {
      ...init,
      headers,
    })
    const text = await response.text()

    let body: unknown = text
    if (text.trim().length > 0) {
      try {
        body = JSON.parse(text)
      } catch {
        body = text
      }
    }

    return {
      status: response.status,
      at: new Date().toISOString(),
      body,
      error:
        response.status >= 400
          ? normalizeError(url, response.status, body, response.headers.get('x-request-id') ?? undefined)
          : undefined,
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'network error'
    return {
      status: 0,
      at: new Date().toISOString(),
      body: { error: message },
      error: {
        code: 'network_error',
        message,
      },
    }
  }
}
