import type { AppError, Envelope } from '../types/contracts'
import { buildRequestHeaders } from './auth-session'

type ApiEnvelopeBody = {
  request_id?: unknown
  idempotency_key?: unknown
  data?: unknown
  error?: unknown
}

function parseBody(text: string): unknown {
  if (text.trim().length === 0) {
    return null
  }

  try {
    return JSON.parse(text) as unknown
  } catch {
    return text
  }
}

function asApiEnvelope(value: unknown): ApiEnvelopeBody | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null
  }
  const maybe = value as ApiEnvelopeBody
  if (!('request_id' in maybe) || !('data' in maybe) || !('error' in maybe)) {
    return null
  }
  return maybe
}

function unwrapSuccessBody<T>(body: unknown): { payload: T; requestId?: string } {
  const envelope = asApiEnvelope(body)
  if (!envelope) {
    return { payload: body as T, requestId: resolveRequestId(body) }
  }
  const requestId =
    typeof envelope.request_id === 'string' && envelope.request_id.length > 0
      ? envelope.request_id
      : undefined
  const data = envelope.data as T
  if (data && typeof data === 'object' && !Array.isArray(data) && requestId) {
    const payloadObject = data as Record<string, unknown>
    if (!('request_id' in payloadObject)) {
      payloadObject.request_id = requestId
    }
  }
  return { payload: data, requestId }
}

function resolveRequestId(value: unknown, fallback?: string): string | undefined {
  if (!value || typeof value !== 'object') {
    return fallback
  }
  const envelope = asApiEnvelope(value)
  if (envelope) {
    const requestId = envelope.request_id
    if (typeof requestId === 'string' && requestId.length > 0) {
      return requestId
    }
  }
  const direct = (value as { request_id?: unknown }).request_id
  if (typeof direct === 'string' && direct.length > 0) {
    return direct
  }
  const nested = (value as { error?: { request_id?: unknown } }).error?.request_id
  if (typeof nested === 'string' && nested.length > 0) {
    return nested
  }
  return fallback
}

function resolveErrorCode(status: number, body: unknown): string {
  const envelope = asApiEnvelope(body)
  if (envelope?.error) {
    return resolveErrorCode(status, envelope.error)
  }
  if (body && typeof body === 'object') {
    const code = (body as { code?: unknown; error?: { code?: unknown } }).code
    if (typeof code === 'string' && code.length > 0) {
      return code
    }
    const nested = (body as { error?: { code?: unknown } }).error?.code
    if (typeof nested === 'string' && nested.length > 0) {
      return nested
    }
  }

  if (status >= 500) {
    return 'upstream_internal_error'
  }
  if (status >= 400) {
    return 'upstream_request_error'
  }
  return 'unknown_error'
}

function resolveErrorMessage(status: number, body: unknown): string {
  const envelope = asApiEnvelope(body)
  if (envelope?.error) {
    return resolveErrorMessage(status, envelope.error)
  }
  if (typeof body === 'string' && body.trim().length > 0) {
    return body
  }

  if (body && typeof body === 'object') {
    const direct = (body as { message?: unknown; error?: { message?: unknown } }).message
    if (typeof direct === 'string' && direct.length > 0) {
      return direct
    }

    const nested = (body as { error?: { message?: unknown } }).error?.message
    if (typeof nested === 'string' && nested.length > 0) {
      return nested
    }
  }

  if (status === 408) {
    return 'request timeout'
  }
  return `request failed (${status})`
}

export function normalizeError(
  _url: string,
  status: number,
  body: unknown,
  fallbackRequestId?: string,
): AppError {
  const envelope = asApiEnvelope(body)
  const errorBody = envelope?.error ?? body
  const requestId =
    typeof envelope?.request_id === 'string' && envelope.request_id.length > 0
      ? envelope.request_id
      : fallbackRequestId
  return {
    code: resolveErrorCode(status, errorBody),
    message: resolveErrorMessage(status, errorBody),
    request_id: resolveRequestId(errorBody, requestId),
  }
}

export function toAppError(error: unknown, fallbackCode = 'unknown_error'): AppError {
  const envelope = asApiEnvelope(error)
  if (envelope?.error) {
    const nested = toAppError(envelope.error, fallbackCode)
    if (
      !nested.request_id &&
      typeof envelope.request_id === 'string' &&
      envelope.request_id.trim().length > 0
    ) {
      nested.request_id = envelope.request_id
    }
    return nested
  }
  if (!error) {
    return { code: fallbackCode, message: 'unknown error' }
  }
  if (typeof error === 'string') {
    return { code: fallbackCode, message: error }
  }
  if (typeof error === 'object') {
    const code = (error as { code?: unknown }).code
    const message = (error as { message?: unknown }).message
    const requestId =
      (error as { request_id?: unknown }).request_id ??
      (error as { error?: { request_id?: unknown } }).error?.request_id
    if (typeof code === 'string' || typeof message === 'string') {
      return {
        code: typeof code === 'string' && code.trim().length ? code : fallbackCode,
        message:
          typeof message === 'string' && message.trim().length ? message : 'request failed',
        request_id: typeof requestId === 'string' && requestId.trim().length ? requestId : undefined,
      }
    }

    const nestedCode = (error as { error?: { code?: unknown } }).error?.code
    const nestedMessage = (error as { error?: { message?: unknown } }).error?.message
    if (typeof nestedCode === 'string' || typeof nestedMessage === 'string') {
      return {
        code: typeof nestedCode === 'string' && nestedCode.trim().length ? nestedCode : fallbackCode,
        message:
          typeof nestedMessage === 'string' && nestedMessage.trim().length
            ? nestedMessage
            : 'request failed',
        request_id: typeof requestId === 'string' && requestId.trim().length ? requestId : undefined,
      }
    }
  }
  return { code: fallbackCode, message: 'unknown error' }
}

export function formatAppError(error: AppError): string {
  const requestSuffix = error.request_id ? ` [rid:${error.request_id}]` : ''
  return `${error.code}: ${error.message}${requestSuffix}`
}

export async function requestEnvelope<T>(
  url: string,
  init?: RequestInit,
): Promise<Envelope<T>> {
  try {
    const headers = await buildRequestHeaders(init?.headers)
    const response = await fetch(url, {
      ...init,
      headers,
    })

    const text = await response.text()
    const body = parseBody(text)
    const responseRequestId = response.headers.get('x-request-id') ?? undefined

    if (response.ok) {
      const { payload } = unwrapSuccessBody<T>(body)
      return {
        ok: true,
        status_code: response.status,
        url,
        payload,
      }
    }

    return {
      ok: false,
      status_code: response.status,
      url,
      error: normalizeError(url, response.status, body, responseRequestId),
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'network error'
    return {
      ok: false,
      status_code: 0,
      url,
      error: {
        code: 'network_error',
        message,
      },
    }
  }
}

export function toErrorMessage(error: unknown): string {
  return formatAppError(toAppError(error))
}
