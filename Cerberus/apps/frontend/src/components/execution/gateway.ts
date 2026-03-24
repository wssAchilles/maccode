import type { GatewayResponse } from './types'

export async function callGateway(path: string, gatewayBase: string, init?: RequestInit): Promise<GatewayResponse> {
  const response = await fetch(`${gatewayBase}${path}`, {
    ...init,
    headers: {
      'content-type': 'application/json',
      ...(init?.headers ?? {}),
    },
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
  }
}
