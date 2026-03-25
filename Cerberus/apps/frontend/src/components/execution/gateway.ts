import { normalizeError } from '../../lib/http'
import { buildRequestHeaders } from '../../lib/auth-session'
import type { GatewayResponse } from './types'

type ApiEnvelopeBody = {
  request_id?: unknown
  data?: unknown
  error?: unknown
}

function asApiEnvelope(value: unknown): ApiEnvelopeBody | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null
  }
  const candidate = value as ApiEnvelopeBody
  if (!('request_id' in candidate) || !('data' in candidate) || !('error' in candidate)) {
    return null
  }
  return candidate
}

function normalizeResponseBody(body: unknown): unknown {
  const envelope = asApiEnvelope(body)
  if (!envelope) {
    return body
  }
  const resolved = envelope.error ?? envelope.data
  if (resolved && typeof resolved === 'object' && !Array.isArray(resolved)) {
    const object = resolved as Record<string, unknown>
    if (
      typeof envelope.request_id === 'string' &&
      envelope.request_id.length > 0 &&
      !('request_id' in object)
    ) {
      object.request_id = envelope.request_id
    }
  }
  return resolved
}

function shouldSetIdempotencyKey(method?: string): boolean {
  const normalized = (method ?? 'GET').toUpperCase()
  return normalized === 'POST' || normalized === 'PUT' || normalized === 'PATCH' || normalized === 'DELETE'
}

function createIdempotencyKey(path: string): string {
  const random =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`
  return `idem:${path}:${random}`
}

export async function callGateway(path: string, gatewayBase: string, init?: RequestInit): Promise<GatewayResponse> {
  const url = `${gatewayBase}${path}`
  try {
    const headers = await buildRequestHeaders(init?.headers)
    if (shouldSetIdempotencyKey(init?.method) && !headers.has('idempotency-key')) {
      const idem = createIdempotencyKey(path)
      headers.set('idempotency-key', idem)
      headers.set('x-idempotency-key', idem)
    }
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

    const normalizedBody = normalizeResponseBody(body)
    return {
      status: response.status,
      at: new Date().toISOString(),
      body: normalizedBody,
      error:
        response.status >= 400
          ? normalizeError(
              url,
              response.status,
              body,
              response.headers.get('x-request-id') ?? undefined,
            )
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
