import { describe, expect, it } from 'vitest'

import { normalizeError } from './http'

describe('normalizeError', () => {
  it('maps structured error payload', () => {
    const error = normalizeError('https://api.example.com', 400, {
      code: 'invalid_request',
      message: 'bad symbol',
      request_id: 'req-123',
    })

    expect(error.code).toBe('invalid_request')
    expect(error.message).toBe('bad symbol')
    expect(error.request_id).toBe('req-123')
  })

  it('provides fallback for upstream server errors', () => {
    const error = normalizeError('https://api.example.com', 500, null)
    expect(error.code).toBe('upstream_internal_error')
    expect(error.message).toContain('request failed')
  })

  it('reads gateway envelope request_id from top-level shell', () => {
    const error = normalizeError('https://api.example.com', 400, {
      request_id: 'rid-shell-1',
      data: null,
      error: {
        code: 'validation_error',
        message: 'bad input',
      },
    })
    expect(error.code).toBe('validation_error')
    expect(error.request_id).toBe('rid-shell-1')
  })
})
