import type { AppError, Envelope } from '../types/contracts'

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

function resolveRequestId(value: unknown): string | undefined {
  if (!value || typeof value !== 'object') {
    return undefined
  }
  const direct = (value as { request_id?: unknown }).request_id
  if (typeof direct === 'string' && direct.length > 0) {
    return direct
  }
  const nested = (value as { error?: { request_id?: unknown } }).error?.request_id
  if (typeof nested === 'string' && nested.length > 0) {
    return nested
  }
  return undefined
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

export function normalizeError(url: string, status: number, body: unknown): AppError {
  return {
    code: resolveErrorCode(status, body),
    message: resolveErrorMessage(status, body),
    request_id: resolveRequestId(body),
  }
}

export async function requestEnvelope<T>(
  url: string,
  init?: RequestInit,
): Promise<Envelope<T>> {
  try {
    const response = await fetch(url, {
      ...init,
      headers: {
        'content-type': 'application/json',
        ...(init?.headers ?? {}),
      },
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
      error: normalizeError(url, response.status, body),
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
  if (!error) {
    return 'unknown error'
  }
  if (typeof error === 'string') {
    return error
  }
  if (typeof error === 'object' && 'message' in error) {
    const message = (error as { message?: unknown }).message
    if (typeof message === 'string' && message.length > 0) {
      return message
    }
  }
  return 'unknown error'
}
