import { describe, expect, it } from 'vitest'

import { readGatewayRequestId } from './types'

describe('readGatewayRequestId', () => {
  it('returns direct request_id when present', () => {
    expect(readGatewayRequestId({ request_id: 'rid-direct' })).toBe('rid-direct')
  })

  it('returns nested error.request_id when direct is missing', () => {
    expect(readGatewayRequestId({ error: { request_id: 'rid-nested' } })).toBe('rid-nested')
  })

  it('returns undefined for unsupported payloads', () => {
    expect(readGatewayRequestId('not-json')).toBeUndefined()
    expect(readGatewayRequestId({})).toBeUndefined()
  })
})
