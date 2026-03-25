import type { AppError, Envelope } from '../types/contracts'
import { buildRequestHeaders } from './auth-session'

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

function resolveRequestId(value: unknown, fallback?: string): string | undefined {
  if (!value || typeof value !== 'object') {
    return fallback
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
  return {
    code: resolveErrorCode(status, body),
    message: resolveErrorMessage(status, body),
    request_id: resolveRequestId(body, fallbackRequestId),
  }
}

export function toAppError(error: unknown, fallbackCode = 'unknown_error'): AppError {
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

    if (response.ok) {
      return {
        ok: true,
        status_code: response.status,
        url,
        payload: body as T,
      }
    }

    return {
      ok: false,
      status_code: response.status,
      url,
      error: normalizeError(url, response.status, body, response.headers.get('x-request-id') ?? undefined),
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
