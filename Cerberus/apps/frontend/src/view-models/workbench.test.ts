import { describe, expect, it } from 'vitest'

import { WORKSPACE_GROUPS, WORKSPACE_MODELS } from './workbench'

describe('workbench workspace registry', () => {
  it('registers the seven web workspaces in order', () => {
    expect(WORKSPACE_MODELS.map((item) => item.id)).toEqual([
      'overview',
      'market',
      'book',
      'strategy',
      'execution',
      'inference',
      'health',
    ])
  })

  it('covers every workspace exactly once across rail groups', () => {
    const groupedIds = WORKSPACE_GROUPS.flatMap((group) => group.items.map((item) => item.id))

    expect(groupedIds).toHaveLength(WORKSPACE_MODELS.length)
    expect(new Set(groupedIds)).toEqual(new Set(WORKSPACE_MODELS.map((item) => item.id)))
  })
})
